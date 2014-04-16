from django.db import models
from django.utils.translation import ugettext_lazy as _

from state_machine.versioning.models import BaseVersionedObject
from gndata_api.utils import *


class BaseGnodeObject(BaseVersionedObject):
    """
    A base class for a versioned G-Node object.
    """
    owner = models.ForeignKey(User, editable=False)

    class Meta:
        abstract = True

    def is_accessible(self, user):
        """ by default object is accessible for it's owner """
        return self.owner == user

    def is_editable(self, user):
        """ by default object is editable for it's owner """
        return self.owner == user

    @classmethod
    def security_filter(cls, queryset, user, update=False):
        return queryset.filter(owner=user.id)


class BaseGnodeObjectWithACL(BaseGnodeObject):
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
                    object_type=self.acl_type,
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
        # FIXME merge somehow into 'share'?

        # first update safety level
        if safety_level and not self.safety_level == safety_level:
            if not int(safety_level) in dict(self.SAFETY_LEVELS).keys():
                raise ValueError("Provided safety level is not valid: %s" % safety_level)
            self.safety_level = safety_level
            self.save()

        # update single user shares
        if not users is None:
            self.share(users)

        # propagate down the hierarchy if cascade
        if cascade:
            for related in self._meta.get_all_related_objects():
                # validate if reversed child can be shared
                if issubclass(related.model, BaseGnodeObjectWithACL):
                    for obj in getattr(self, related.get_accessor_name()).all():
                        obj.acl_update(safety_level, users, cascade)

    @property
    def shared_with(self):
        """ returns a QuerySet of all specific accesses. Method relies on 
        'parent' object's ID and type (this is an abstract class anyway) """
        return SingleAccess.objects.filter(object_id=self.local_id,
                                           object_type=self.acl_type)

    @property
    def acl_type(self):
        """ object type for direct permissions """
        return self.__class__.__name__.lower()

    @property
    def access_list(self):
        """ returns list of users having personal access to the object """
        return [x.access_for for x in self.shared_with]

    @property
    def is_public(self):
        return self.safety_level == 1

    @property
    def is_friendly(self):
        return self.safety_level == 2

    @property
    def is_private(self):
        return self.safety_level == 3

    def get_access_for_user(self, user):
        """ returns appropriate SingleAccess object, if a given user has access 
        to this object """
        return self.shared_with.get(access_for=user)

    def is_accessible(self, user):
        """ Defines whether an object (Datafile etc) is accessible for a given
        user (either readable or editable) """
        return self.is_public or (user in self.access_list) \
               or self.owner == user

    def is_editable(self, user):
        """ User may edit if:
        - user is an owner, or
        - user has a direct access with level 2 (edit)
        """
        return self.owner == user or \
               (user in self.access_list and
                self.get_access_for_user(user).access_level == 2)

    @classmethod
    def security_filter(cls, queryset, user, update=False):
        """ filters given queryset for objects available for a given user. Does
        not evaluate QuerySet, does not hit the database. """

        if not issubclass(queryset.model, cls):
            raise ReferenceError("Cannot filter queryset of an alien type.")

        if not update:
            # 1. all public objects
            q1 = queryset.filter(safety_level=1).exclude(owner=user.id)

            # 2. all *friendly*-shared objects are currently skipped

            # 3. All private direct shares
            direct_shares = SingleAccess.objects.filter(
                access_for=user.id,
                object_type=queryset.model.acl_type
            )
            dir_acc = [sa.object_id for sa in direct_shares]
            q3 = queryset.filter(pk__in=dir_acc)

            perm_filtered = q1 | q3

        else:
            # 1. All private direct shares with 'edit' level
            direct_shares = SingleAccess.objects.filter(
                access_for=user.id,
                object_type=queryset.model.acl_type,
                access_level=2
            )
            dir_acc = [sa.object_id for sa in direct_shares]

            # not to damage QuerySet
            perm_filtered = queryset.filter(pk__in=dir_acc)

        # owned objects always available
        return perm_filtered | queryset.filter(owner=user.id)


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
    access_for = models.ForeignKey(User)  # with whom it is shared
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
        if hasattr(self.model, 'acl_type') and issubclass(self.model, BaseGnodeObject) and user:
            # fetch single accesses for all objects
            accs = SingleAccess.objects.filter(object_id__in=ids,
                                               object_type=self.model.acl_type)

            # parse accesses to objects
            for obj in objects:
                sw = dict([(sa.access_for.username, sa.access_level) \
                           for sa in accs if sa.object_id == obj.pk])
                if user.pk == obj.owner_id:  # not to hit DB to fetch user
                    setattr(obj, '_shared_with', sw or None)
                else:
                    setattr(obj, '_shared_with', None)

        return objects