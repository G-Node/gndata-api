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

        # do not show fields with None values
        is_valid = lambda x: x[1] is not None
        attrs = filter(is_valid, [(name, getattr(self, name)) for name in allowed])

        # convert datetime to string
        attrs = [(k, v.strftime("%y-%m-%d")) if hasattr(v, 'strftime') else (k, v) for k, v in attrs]

        # show name field first, if exists
        try:
            name_index = [k for k, v in attrs].index('name')
            attrs.insert(0, attrs.pop(name_index))
        except ValueError:
            pass  # name attribute does not exist

        return ", ".join(["%s: %s" % (k, str(v)) for k, v in attrs])

    def is_accessible(self, user):
        """ by default object is accessible for it's owner """
        return self.owner == user

    def is_editable(self, user):
        """ by default object is editable for it's owner """
        return self.owner == user

    @classmethod
    def security_filter(cls, queryset, user, update=False):
        return queryset.filter(owner=user.id)