from django.db import models
from django.contrib.auth.models import User

from state_machine.versioning.models import BaseVersionedObject


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