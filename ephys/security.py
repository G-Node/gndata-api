from permissions.models import BasePermissionsMixin, SingleAccess


class BlockBasedPermissionsMixin(BasePermissionsMixin):
    """
    Abstract class that implements access management methods for objects with
    Block-dependent security.
    """

    class Meta:
        abstract = True

    def is_accessible(self, user):
        block = self.block
        return block.is_public or (user in block.access_list) or self.owner == user

    def is_editable(self, user):
        block = self.block
        return (user in block.access_list and
                block.get_access_for_user(user).access_level == 2) \
            or self.owner == user

    @classmethod
    def security_filter(cls, queryset, user, update=False):
        if not issubclass(queryset.model, cls):
            raise ReferenceError("Cannot filter queryset of an alien type.")

        if not update:
            # all public objects
            q1 = queryset.filter(safety_level=1).exclude(owner=user.id)

            # all private direct shares
            direct_shares = SingleAccess.objects.filter(
                access_for=user.id,
                object_type='block'
            )
            dir_acc = [sa.object_id for sa in direct_shares]
            q2 = queryset.filter(block_id__in=dir_acc)

            perm_filtered = q1 | q2

        else:
            # all private direct shares with 'edit' level
            direct_shares = SingleAccess.objects.filter(
                access_for=user.id,
                object_type='block',
                access_level=2
            )
            dir_acc = [sa.object_id for sa in direct_shares]

            # not to damage QuerySet
            perm_filtered = queryset.filter(block_id__in=dir_acc)

        # owned objects always available
        return perm_filtered | queryset.filter(owner=user.id)