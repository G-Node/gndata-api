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

    def __unicode__(self):
        no_render = ['local_id', 'guid', 'starts_at', 'ends_at']
        test = lambda x: not x.name in no_render and not isinstance(x, models.ForeignKey)
        allowed = [f.name for f in self._meta.local_fields if test(f)]

        is_valid = lambda x: x[1] is not None
        attrs = filter(is_valid, [(name, getattr(self, name)) for name in allowed])

        return ", ".join(["%s: %s" % (k, str(v)) for k, v in dict(attrs).items()])

    def is_accessible(self, user):
        """ by default object is accessible for it's owner """
        return self.owner == user

    def is_editable(self, user):
        """ by default object is editable for it's owner """
        return self.owner == user

    @classmethod
    def security_filter(cls, queryset, user, update=False):
        return queryset.filter(owner=user.id)