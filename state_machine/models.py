from datetime import datetime

from django.db import models
from django.utils.translation import ugettext_lazy as _

from managers import VersionManager, VersionedM2MManager, VersionedObjectManager
from gndata_api.utils import *


"""
Basic Version Control implementation features.


1. Database representation
--------------------------------------------------------------------------------
a) Table for a versioned model
every object has 'starts_at' and 'ends_at' fields. Current (latest) object 
version always has 'ends_at' = NULL, all previous versions have 'ends_at' set 
with the datetime equals to the 'starts_at' field of the next version. Thus 
every version is a new row in the database; all unchanged attributes are 
redundantly copied.

b) How do foreign keys work
we make django think that 'local_id' (non-unique across versions) is the PK for
any model. This allows using normal django ORM (calling lazy relations like 
event.segment etc.), and to avoid duplicated by fetching several object 
versions, we set an additional filters on the original object manager, as well 
as we proxy these filters to the managers that fetch related objects. 
Intuitively it could be understood looking at the SQL level: the extended 
relations managers make every SQL request to the database containing constraints
on all JOINs (like 'ends_at' = NULL), thus fetching only single version of any 
relation object.

c) Table holding M2M relationship between versioned models
M2M relations are also versioned. To support that we created a base class that 
supports versioning ('VersionedM2M'), which should be used as a proxy model for
versioned M2M relations. This 'VersionedM2M' class stands 'in between' two 
models and holds versioned references to both of them, and replaces default 
django-based M2M relation manager class.


2. A trick with Primary Key
--------------------------------------------------------------------------------
By default the PK for every versioned model to a non-auto incremental 'local_id' 
field. This field is updated manually and is actually unique across objects but 
not across versions of the same object as well as not unique across rows in the 
DB table, so all versions of the same object have the same 'local_id' value. 
This PK is needed for django to auto-build relationships via FKs and M2Ms.
However, to get the correct database behaviour after the initial table creation 
the custom SQL changes this PK to the real globally unique PK field called 
'guid' - every versioned model has it (see 'ObjectState' class).


3. Base class supporting versioning for other apps
--------------------------------------------------------------------------------
All versioned models should inherit from 'ObjectState'. In this base class all
features of the versioned object are implemented.


4. Model manager
--------------------------------------------------------------------------------
To support versioning, managers are extended with '_at_time' attribute, used in 
case some older object version is requested. Manager sets appropriate filters on
the QuerySet when 'at_time' parameter is provided in the request (MUST be always
a first filter, for example:

VersionedManager.filter(at_time='2012-07-26 17:16:12').filter(...))


5. Versioned QuerySet
--------------------------------------------------------------------------------
is extended with the automatic support for timing of the objects to fetch from 
the db, thus implementing object versioning.


6. ORM extentions that support lazy relations
--------------------------------------------------------------------------------
important:
 - use VersionedForeignKey instead of ForeignKey field
 - create M2Ms 'through' model, subclassed from 'VersionedM2M' class

this allows relations to be versioned.

a) Reverse Single Related:
is implemented by overriding a ForeignKey class by VersionedForeignKey, namely 
the 'contribute_to_class' method to assign different descriptor at instance 
initialization time. New descriptor (VReverseSingleRelatedObjectDescriptor 
class) differs only by the 'get_query_set' method, which returns a correct 
VersionedQuerySet instance that supports versioning and hits the database with 
time, equal to the time of the original object, when appropriate parent object 
is called. 

b) Foreign Related and all M2M Objects:
all '<object_type>_set' attributes are wrapped in the base class (ObjectState) 
in __getattribute__ by assigning the time to the RelatedManager, returned by 
default by the '<object_type>_set' descriptor. Thus the RelatedManager knows 
about timing to request related objects from the database, equal to the time of
the original object.

"""


#===============================================================================
# Base models for a Versioned Object, M2M relations and Permissions management
#===============================================================================


class VersionedM2M(models.Model):
    """ this abstract model is used as a connection between two objects for many 
    to many relationship for versioned objects instead of ManyToMany field. """

    date_created = models.DateTimeField(editable=False)
    starts_at = models.DateTimeField(serialize=False, default=datetime.now, editable=False)
    ends_at = models.DateTimeField(serialize=False, blank=True, null=True, editable=False)
    objects = VersionedM2MManager()

    class Meta:
        abstract = True


class ObjectState(models.Model):
    """
    A base class for a versioned G-Node object.

    Versioning is implemented as "full copy" mode. For every change, a new 
    revision is created and a new version of the object is created.

    There are two types of object IDs:
    - 'guid' - a hash of an object, a unique global object identifier (GUID)
    - 'local_id' - object ID invariant across object versions

    """
    # global ID, distinct for every object version = unique table PK
    guid = models.CharField(max_length=40, editable=False)
    # local ID, invariant between object versions, distinct between objects
    # local ID + starts_at basically making a PK
    local_id = models.BigIntegerField('LID', primary_key=True, editable=False)
    owner = models.ForeignKey(User, editable=False)
    date_created = models.DateTimeField(editable=False)
    starts_at = models.DateTimeField(serialize=False, default=datetime.now, editable=False)
    ends_at = models.DateTimeField(serialize=False, blank=True, null=True, editable=False)
    objects = VersionedObjectManager()
    _at_time = None  # indicates an older version for object instance

    class Meta:
        abstract = True

    def __getattribute__(self, name):
        """ wrap getting object attributes to catch calls to related managers,
        which require '_at_time' parameter to retrieve related objects at time,
        equal to the original object.

        Direct FK, direct M2M or reverse M2M related manager is requested. By
        adding '_at_time' attribute we make the related manager support
        versioning by requesting related objects at the time equal to the
        original object ('self' in this case). For reverse FKs (like
        'event.segment') we need to override related descriptor, see
        'VersionedForeignKey' field class. """
        attr = object.__getattribute__(self, name)
        if isinstance(attr, VersionManager) and self._at_time:
            attr._at_time = self._at_time
        return attr

    @property
    def local_id_as_str(self):
        """ base32hex string representation of an ID """
        return base32str(self.local_id)

    @property
    def get_type(self):
        """ every object has a type defined as lowercase name of the class. """
        return self.__class__.__name__.lower()

    def natural_key(self):
        return {
            "local_id": self.local_id,
            "last_modified": self.starts_at,
            "guid": self.guid }

    def get_absolute_url(self):
        """ by default this should be similar to that """
        return ''.join(['/', get_type(self), '/', self.local_id_as_str, '/'])

    def get_owner(self):
        """ required for filtering by owner in REST """
        return self.owner

    def is_active(self):
        return not self.ends_at

    def is_accessible(self, user):
        """ by default object is accessible for it's owner """
        return self.owner == user

    def delete(self, using=None):
        """ uses queryset delete() method to perform versioned deletion """
        self.__class__.objects.filter(pk=self.pk).delete(using=using)

    def save(self, *args, **kwargs):
        """ implements versioning by always saving new object. This should be
        already an atomic operation """

        now = datetime.now()

        guid_to_delete = None
        if self.guid:  # existing object, need to "close" old version later
            guid_to_delete = self.guid

        else:  # new object
            self.local_id = get_new_local_id()

        self.date_created = self.date_created or now
        self.starts_at = now
        self.guid = create_hash_from(self)
        self.full_clean()

        kwargs['force_insert'] = True
        super(ObjectState, self).save(*args, **kwargs)

        if guid_to_delete is not None:
            self.__class__.objects.filter(guid=guid_to_delete).delete()


class SafetyLevel(models.Model):
    """
    Safety level represents a level of access to an object by other users. An 
    object can be Public (all users have access), Friendly (all "friends" have 
    access) and Private (owner and special assignments only). Also handles 
    special assignments (access for special users from the list with 'read-only'
    or 'contributor' access levels).
    """
    SAFETY_LEVELS = (
        (1, _('Public')),
        (2, _('Friendly')),
        (3, _('Private')),
    )
    safety_level = models.IntegerField('privacy_level', choices=SAFETY_LEVELS, default=3)

    class Meta:
        abstract = True

    def share(self, users):
        """ performs an update of all personal accesses to an object;
        users is a dict of the form {'user_id': 'access level', } """
        def validate_user(user):
            try:
                return User.objects.get(pk=int(user_id))
            except:
                raise ValueError("Provided user ID is not valid: %s" % user_id)

        current_users = [x.access_for for x in self.shared_with]
        users_to_remove = list(set([x.id for x in current_users]) - set(users.keys()))

        for user_id, level in users.items():
            u = validate_user(user_id)

            if level not in dict(SingleAccess.ACCESS_LEVELS).keys():
                raise ValueError("Provided access level for the user ID %s \
                    is not valid: %s" % (user_id, level))

            if u in current_users:  # update access level
                p = self.shared_with.get(access_for=u)
                p.access_level = level
                p.save()

            else:  # create new access
                SingleAccess(
                    object_id=self.local_id,
                    object_type=self.acl_type(),
                    access_for=u,
                    access_level=level
                ).save()

        for u in users_to_remove:  # delete legacy accesses
            self.shared_with.get(access_for=u).delete()

    def acl_update(self, safety_level=None, users=None, cascade=False):
        """ update object safety level and direct user permissions (cascade).
        Note.

        - safety_level is an int (see self.SAFETY_LEVELS)
        - users is a dict { <user_id>: <access_level>, } (see ACCESS_LEVELS)
        """

        # first update safety level
        if safety_level and not self.safety_level == safety_level:
            if not int(safety_level) in dict(self.SAFETY_LEVELS).keys():
                raise ValueError("Provided safety level is not valid: %s" % safety_level)
            self.safety_level = safety_level
            self.save()

        # update single user shares
        if not users == None:
            self.share(users)

        # propagate down the hierarchy if cascade
        if cascade:
            for related in self._meta.get_all_related_objects():
                # validate if reversed child can be shared
                if issubclass(related.model, SafetyLevel):
                    for obj in getattr(self, related.get_accessor_name()).all():
                        obj.acl_update(safety_level, users, cascade)

    @property
    def shared_with(self):
        """ returns a QuerySet of all specific accesses. Method relies on 
        'parent' object's ID and type (this is an abstract class anyway) """
        return SingleAccess.objects.filter(object_id=self.local_id,
                                           object_type=self.acl_type())

    @classmethod
    def security_filter(cls, queryset, user, update=False):
        """ filters given queryset for objects available for a given user. Does 
        not evaluate QuerySet, does not hit the database. """

        #if not "owner" in [x.name for x in queryset.model._meta.local_fields]:
        #    return queryset  # non-multiuser objects are fully available
        if not issubclass(queryset.model, cls):
            return queryset  # non-multiuser objects are fully available

        if issubclass(queryset.model, cls):
            if not update:
                # 1. all public objects 
                q1 = queryset.filter(safety_level=1).exclude(owner=user)

                # 2. all *friendly*-shared objects are currently skipped

                # 3. All private direct shares
                direct_shares = SingleAccess.objects.filter(
                    access_for=user,
                    object_type=queryset.model.acl_type()
                )
                dir_acc = [sa.object_id for sa in direct_shares]
                q3 = queryset.filter(pk__in=dir_acc)

                perm_filtered = q1 | q3

            else:
                # 1. All private direct shares with 'edit' level
                direct_shares = SingleAccess.objects.filter(
                    access_for=user,
                    object_type=queryset.model.acl_type(),
                    access_level=2
                )
                dir_acc = [sa.object_id for sa in direct_shares]

                # not to damage QuerySet
                perm_filtered = queryset.filter(pk__in=dir_acc)
        else:
            perm_filtered = queryset.none()

        # owned objects always available
        queryset = perm_filtered | queryset.filter(owner=user)
        return queryset

    @classmethod
    def acl_type(cls):
        """ object type for direct permissions. normally the lowercase name of 
        the class """
        return cls.__name__.lower()

    def access_list(self):
        """ returns list of users having personal access to the object """
        return [x.access_for for x in self.shared_with]

    def remove_all_shares(self):
        raise NotImplementedError

    def is_public(self):
        return self.safety_level == 1

    def is_friendly(self):
        return self.safety_level == 2

    def is_private(self):
        return self.safety_level == 3

    def get_access_for_user(self, user):
        """ returns appropriate SingleAccess object, if a given user has access 
        to this object """
        return self.shared_with.get(access_for=user)

    def is_accessible(self, user):
        """ Defines whether an object (Datafile etc) is accessible for a given
        user (either readable or editable) """
        return self.is_readable(user) or self.is_editable(user)

    def is_readable(self, user):
        return self.is_editable(user) or self.is_public() or \
               (user in self.access_list()) or self.owner == user

    def is_editable(self, user):
        """ User may edit if:
        - user is an owner, or
        - user has a direct access with level 2 (edit)
        """
        return self.owner == user or \
               (user in self.access_list() and
                self.get_access_for_user(user).access_level == 2)


class SingleAccess(models.Model):
    """
    Represents a single connection between an object (Section, Datafile etc.) 
    and a User, with whom the object is shared + the level of this sharing 
    ('read-only' or 'can edit' etc.).

    IMPORTANT: if you need object to have single accesses you have to define a
    acl_type method for it (see example with 'Section').

    Note: Permissions are NOT version controlled.
    """
    ACCESS_LEVELS = (
        (1, _('Read-only')),
        (2, _('Edit')),
    )
    object_id = models.BigIntegerField()  # local ID of the shareable object
    object_type = models.CharField(max_length=30)
    # the pair above identifies a unique object for ACL record
    access_for = models.ForeignKey(User) # with whom it is shared
    access_level = models.IntegerField(choices=ACCESS_LEVELS, default=1)


#===============================================================================
# Classes supporting utilities
#===============================================================================

# TODO refactor out
class ObjectExtender(object):
    """ used to extend a list of given homogenious objects with additional 
    attributes. For every given object it assigns:
    - children permalinks
    - permalinks of related m2m objects
    - acl settings
    """
    model = None

    def __init__(self, model):
        self.model = model

    def fill_acl(self, objects, user=None):
        """ extends every object in a given list with _shared_with dict with 
        current object's acl settings """
        if not objects: return []

        ids = [ x.pk for x in objects ]

        # check if the model is multi-user
        if hasattr(self.model, 'acl_type') and issubclass(self.model, ObjectState) and user:
            # fetch single accesses for all objects
            accs = SingleAccess.objects.filter(object_id__in=ids,
                                               object_type=self.model.acl_type())

            # parse accesses to objects
            for obj in objects:
                sw = dict([(sa.access_for.username, sa.access_level) \
                           for sa in accs if sa.object_id == obj.pk])
                if user.pk == obj.owner_id:  # not to hit DB to fetch user
                    setattr(obj, '_shared_with', sw or None)
                else:
                    setattr(obj, '_shared_with', None)

        return objects