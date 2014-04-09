from datetime import datetime

import numpy as np

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

    # TODO remove this as deprecated or make transaction.atomic decorated
    def acl_update(self, safety_level=None, users=None, cascade=False):
        """ update object safety level and direct user permissions (cascade).
        Note. This function works with single objects and not very effective 
        with bulk acl object updates (when propagation down the tree needed). 
        For efficiency look at 'bulk_acl_update' classmethod. 

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
                if issubclass(related.model, SafetyLevel): # reversed child can be shared
                    for obj in getattr(self, related.get_accessor_name()).all():
                        obj.acl_update(safety_level, users, cascade)

    # TODO insert here transaction.atomic decorator
    @classmethod
    def bulk_acl_update(self, objects, safety_level=None, users=None, cascade=False):
        """ bulk acl update for homogenious (?) list of objects. The difference 
        from the similar acl_update method is the speed of the update (this 
        method makes less SQL hits) 

        - safety_level is an int (see self.SAFETY_LEVELS)
        - users is a dict { <user_id>: <access_level>, } (see ACCESS_LEVELS)
        """
        if safety_level:  # update safety level - in bulk
            for_update = {}
            for obj in objects:
                if not (obj.safety_level == safety_level):
                    if not for_update.has_key(obj.__class__):
                        for_update[ obj.__class__ ] = []
                    # collect objects to update for every class type
                    for_update[ obj.__class__ ].append(obj)

            # perform bulk updates, one sql for every class type
            for model, objs in for_update.items():
                model.save_changes(objs, {'safety_level': safety_level}, {}, {}, False)

        # update single user shares. assumes users are cleaned (exist)
        if not users is None:
            obj_map = {}  # dict {<obj_type>: [<object_pk>, ..], }
            for obj in objects:
                obj_type = get_type(obj)
                if not obj_map.has_key(obj_type):
                    obj_map[obj_type] = []
                obj_map[obj_type].append(obj.pk)

            # remove old accesses
            for obj_type, ids in obj_map.items():
                old = SingleAccess.objects.filter(object_type=obj_type)
                old.filter(object_id__in=ids).delete()

            # create new access records
            new_accesses = []
            for obj in objects:
                for user_id, access_level in users.items():
                    new_acc = SingleAccess(
                        object_id=obj.pk,
                        object_type=get_type(obj),
                        access_for_id=user_id,
                        access_level=access_level
                    )
                    new_accesses.append(new_acc)
            SingleAccess.objects.bulk_create(new_accesses)

        # propagate down the hierarchy if cascade
        if cascade:
            for_update = [] # collector for children to update (heterogenious ?)
            obj_map = {}  # dict {<obj_class>: [<obj>, ..], }
            for obj in objects:  # TODO make a separate builder for that
                cls = obj.__class__
                if not obj_map.has_key(cls):
                    obj_map[ cls ] = []
                obj_map[ cls ].append(obj)

            for cls, objs in obj_map.items():
                ext = ObjectExtender(cls)
                obj_with_related = ext.fill_fks(objects = objs)

                for related in cls._meta.get_all_related_objects():
                    # cascade down only for reversed children that can be shared
                    if issubclass(related.model, SafetyLevel):

                        # collector for children IDs: for every obj from given
                        # objects collect children ids to update, by type
                        # (related)
                        ids_upd = []
                        for obj in obj_with_related:
                            ids_upd += getattr(obj, related.get_accessor_name() + '_buffer_ids')

                        # all children of 'related' type
                        for_update += list(related.model.objects.filter(pk__in=ids_upd))

            if for_update:
                self.bulk_acl_update(for_update, safety_level, users, cascade)

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

    def fill_relations(self, objects, user=None, _at_time=None):
        """ extends every object in a given list with children and m2m
        permalinks """
        if not objects:
            return None

        if len(objects) > 0: # evaluates queryset if not done yet
            # fetch reversed FKs (children)
            objects = self.fill_fks(objects, user, _at_time)

            # fetch reversed M2Ms (m2m children)
            objects = self.fill_m2m(objects, user, _at_time)

        return objects

    def fill_fks(self, objects, user=None, _at_time=None):
        """ assigns permalinks of the reversed-related children to the list of 
        objects given. Expects list of objects, uses reversed FKs to fetch 
        children and their ids. Returns same list of objects, each having new  
        attributes WITH postfix _buffer and _buffer_ids after default django 
        <fk_name>_set field, containing list of reversly related FK object 
        permalinks and ids respectively.

        Used primarily in REST. 
        """
        if not objects: return []

        ids = [ x.pk for x in objects ]

        flds = [f for f in self.model._meta.get_all_related_objects() if not \
                                                                             issubclass(f.model, VersionedM2M) and issubclass(f.model, ObjectState)]
        related_names = [f.field.rel.related_name or get_type(f.model) + "_set" for f in flds]
        # FK relations - loop over related managers / models
        for rel_name in related_names:

            # get all related objects for all requested objects as one SQL
            rel_manager = getattr(self.model, rel_name)
            rel_field_name = rel_manager.related.field.name
            rel_model = rel_manager.related.model

            # fetching reverse relatives of type rel_name:
            filt = { rel_field_name + '__in': ids }
            if _at_time and issubclass(rel_model, ObjectState): # proxy time if requested
                filt = dict(filt, **{"at_time": _at_time})
            # relmap is a list of pairs (<child_id>, <parent_ref_id>)
            rel_objs = rel_model.objects.filter(**filt)
            if user:
                rel_objs = SafetyLevel.security_filter(rel_objs, user)

            relmap = rel_objs.values_list('pk', rel_field_name)

            if relmap:
                # preparing fk maps: preparing dicts with keys as parent 
                # object ids, and lists with related children links and ids.
                fk_map_plinks = {}
                fk_map_ids = {}
                mp = np.array(relmap)
                fks = set(mp[:, 1])
                for i in fks:
                    fk_map_ids[int(i)] = [ x for x in mp[ mp[:,1]==i ][:,0] ]
                    fk_map_plinks[int(i)] = [ build_obj_location(rel_model, x) \
                                              for x in fk_map_ids[int(i)] ]

                for obj in objects: # parse children into attrs
                    try:
                        setattr(obj, rel_name + "_buffer", fk_map_plinks[obj.pk])
                        setattr(obj, rel_name + "_buffer_ids", fk_map_ids[obj.pk])
                    except KeyError: # no children, but that's ok
                        setattr(obj, rel_name + "_buffer", [])
                        setattr(obj, rel_name + "_buffer_ids", [])
            else:
                # objects do not have any children of that type
                for obj in objects:
                    setattr(obj, rel_name + "_buffer", [])
                    setattr(obj, rel_name + "_buffer_ids", [])
        return objects

    def fill_m2m(self, objects, user=None, _at_time=None):
        """ assigns permalinks of the related m2m children to the list of 
        objects given. Expects list of objects, uses m2m to fetch children with 
        their ids. Returns same list of objects, each having new attribute WITH 
        postfix _buffer and _buffer_ids after default django <m2m_name> field, 
        containing list of m2m related object permalinks and ids respectively. 
        """
        if not objects: return []

        ids = [ obj.pk for obj in objects ]

        fields = self.model._meta.many_to_many

        # add reversed m2m, currently only for RCG
        if get_type(self.model) == 'recordingchannelgroup': # 
            fields.append(self.model.recordingchannel_set.related.field)

        # m2m defined on the model side
        for field in fields:
            m2m_class = field.rel.through

            if get_type(field.model) == get_type(self.model):
                # direct m2m relationship
                own_name = field.m2m_field_name()
                rev_name = field.m2m_reverse_field_name()
                rev_model = field.related.parent_model
                url_base = get_url_base(field.rel.to)
                obj_field_name = field.name

            else:
                # reverse m2m relationship
                own_name = field.m2m_reverse_field_name()
                rev_name = field.m2m_field_name()
                rev_model = field.model
                url_base = get_url_base(field.model)
                obj_field_name = rev_name + '_set'

            filt = dict([(own_name + '__in', ids)])

            # proxy time if requested
            if _at_time and issubclass(m2m_class, VersionedM2M):
                filt = dict(filt, **{"at_time": _at_time})

            # select all related m2m connections (not reversed objects!) of 
            # a specific type, one SQL
            rel_m2ms = m2m_class.objects.filter(**filt).select_related(rev_name)

            # get evaluated m2m conn queryset:
            rel_m2m_map = [ (getattr(r, own_name + "_id"), getattr(r, rev_name + "_id")) for r in rel_m2ms ]

            if user and rel_m2m_map: # security filtering
                # proxy time if needed
                if _at_time and issubclass(rev_model, ObjectState):
                    available = rev_model.objects.filter(at_time=_at_time)
                else:
                    available = rev_model.objects.all()
                available = SafetyLevel.security_filter(available, user).values_list('pk', flat=True)
                rel_m2m_map = [x for x in rel_m2m_map if x[1] in available]

            if rel_m2m_map:
                # preparing m2m maps: preparing dicts with keys as parent 
                # object ids, and lists with m2m related children links and ids.
                m2m_map_plinks = {}
                m2m_map_ids = {}
                mp = np.array(rel_m2m_map)
                fks = set(mp[:, 0])

                for i in fks:
                    m2m_map_ids[int(i)] = [ int(x) for x in mp[ mp[:,0]==i ][:,1] ]
                    m2m_map_plinks[int(i)] = [ build_obj_location(rev_model, x) \
                                               for x in m2m_map_ids[int(i)] ]

                for obj in objects: # parse children into attrs
                    try:
                        setattr(obj, obj_field_name + '_buffer', m2m_map_plinks[ obj.pk ])
                        setattr(obj, obj_field_name + '_buffer_ids', m2m_map_ids[ obj.pk ])
                    except KeyError: # no children, but that's ok
                        setattr(obj, obj_field_name + '_buffer', [])
                        setattr(obj, obj_field_name + '_buffer_ids', [])
            else:
                # objects do not have any m2ms of that type
                for obj in objects:
                    setattr(obj, obj_field_name + '_buffer', [])
                    setattr(obj, obj_field_name + '_buffer_ids', [])

        return objects

