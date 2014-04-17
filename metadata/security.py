from permissions.models import BasePermissionsMixin, SingleAccess


class DocumentBasedPermissionsMixin(BasePermissionsMixin):
    """
    Abstract class that implements access management methods for objects with
    Document-dependent security.
    """

    class Meta:
        abstract = True

    def is_accessible(self, user):
        doc = self.document
        return doc.is_public or (user in doc.access_list) or self.owner == user

    def is_editable(self, user):
        doc = self.document
        return (user in doc.access_list and
                doc.get_access_for_user(user).access_level == 2) \
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
                object_type='document'
            )
            dir_acc = [sa.object_id for sa in direct_shares]
            q2 = queryset.filter(document_id__in=dir_acc)

            perm_filtered = q1 | q2

        else:
            # all private direct shares with 'edit' level
            direct_shares = SingleAccess.objects.filter(
                access_for=user.id,
                object_type='document',
                access_level=2
            )
            dir_acc = [sa.object_id for sa in direct_shares]

            # not to damage QuerySet
            perm_filtered = queryset.filter(document_id__in=dir_acc)

        # owned objects always available
        return perm_filtered | queryset.filter(owner=user.id)