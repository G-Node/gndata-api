from django.db import models
from django.utils import timezone

from state_machine.versioning.managers import VersionManager
from state_machine.versioning.managers import VersionedObjectManager
from state_machine.versioning.managers import VersionedM2MManager
from gndata_api.utils import *

import uuid

#===============================================================================
# Base models for a simple Versioned Object, M2M relations
#===============================================================================


class BaseVersionedObject(models.Model):
    """
    this is an abstract class that has basic fields needed for versioning and
    implements key versioned operations like save or delete.
    """
    # global ID, distinct for every object version = unique table PK
    guid = models.CharField(max_length=40, editable=False)
    date_created = models.DateTimeField(editable=False)
    starts_at = models.DateTimeField(serialize=False, default=timezone.now, editable=False)
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

    def delete(self, using=None):
        """ uses queryset delete() method to perform versioned deletion """
        self.__class__.objects.filter(pk=self.pk).delete()

    def save(self, *args, **kwargs):
        """ implements versioning by always saving new object. This should be
        already an atomic operation """

        now = timezone.now()

        guid_to_delete = None
        if self.guid:  # existing object, need to "close" old version later
            guid_to_delete = self.guid

        else:  # new object
            self.local_id = get_new_local_id()

        self.date_created = self.date_created or now
        self.starts_at = now
        self.guid = uuid.uuid1().hex
        self.full_clean()

        kwargs['force_insert'] = True
        super(BaseVersionedObject, self).save(*args, **kwargs)

        if guid_to_delete is not None:
            self.__class__.objects.filter(guid=guid_to_delete).delete()


class VersionedM2M(BaseVersionedObject):
    """ this abstract model is used as a connection between two objects for many 
    to many relationship for versioned objects instead of ManyToMany field. """

    objects = VersionedM2MManager()

    class Meta:
        abstract = True