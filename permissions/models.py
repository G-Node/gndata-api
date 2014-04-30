from django.db import models
from django.contrib.auth.models import User
from gndata_api.utils import *


class BasePermissionsMixin(models.Model):
    """
    Safety level represents a level of access to an object by other users. An
    object can be Public (all users have access), Friendly (all "friends" have
    access) and Private (owner and special assignments only). Also handles
    special assignments (access for special users from the list with 'read-only'
    or 'contributor' access levels).
    """
    SAFETY_LEVELS = (
        (1, 'Public'),
        (2, 'Friendly'),
        (3, 'Private'),
    )
    safety_level = models.IntegerField('privacy_level', choices=SAFETY_LEVELS, default=3)

    class Meta:
        abstract = True

    def share(self, users):
        """ performs an update of the related ACL.

        :param  users   new personal accesses to an object
        :type   users   {'<user_id>': <access_level>, ...}

        """
        def validate_user(user_id):
            return User.objects.get(pk=int(user_id))

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
        (1, 'Read-only'),
        (2, 'Edit'),
    )
    object_id = models.CharField(max_length=10)  # local ID of the shared object
    object_type = models.CharField(max_length=30)
    # the pair above identifies a unique object for ACL record
    access_for = models.ForeignKey(User)  # with whom it is shared
    access_level = models.IntegerField(choices=ACCESS_LEVELS, default=1)