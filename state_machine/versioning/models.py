from django.db import models
from django.utils import timezone

from state_machine.versioning.managers import VersionManager
from state_machine.versioning.managers import VersionedObjectManager
from state_machine.versioning.managers import VersionedM2MManager

from gndata_api.utils import base32str

#===============================================================================
# Base models for a simple Versioned Object, M2M relations
#===============================================================================


class BaseVersionedObject(models.Model):
    """
    A base class for a versioned G-Node object.

    Versioning is implemented as "full copy" mode. For every change, a new
    revision is created and a new version of the object is created.

    There are two types of object IDs:
    - 'guid' - a hash of an object, a unique global object identifier (GUID)
    - 'local_id' - object ID invariant across object versions
    """
    # global ID, distinct for every object version = unique table PK
    # PRIMARY KEY must be swapped with local_id on the database
    # this is the main cheat: let Django assume that local_id is the primary
    # key and manage objects transparently from object versions. Database
    # handles primary key column as a different column instead.
    guid = models.CharField(max_length=40, editable=False)
    # local ID, invariant between object versions, distinct between objects
    # local ID + starts_at also making a 'real' PK
    #local_id = models.BigIntegerField('LID', primary_key=True, editable=False)
    local_id = models.CharField(max_length=10, primary_key=True, editable=False)
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
        # update if self exists in the DB else create?
        self.__class__.objects.bulk_create([self])

    @property
    def get_type(self):
        """ every object has a type defined as lowercase name of the class. """
        return self.__class__.__name__.lower()

    def natural_key(self):
        return {
            "local_id": self.local_id,
            "last_modified": self.starts_at,
            "guid": self.guid
        }

    def get_absolute_url(self):
        """ by default this should be similar to that """
        return ''.join(['/', self.get_type, '/', self.local_id, '/'])

    def is_active(self):
        return not self.ends_at


class VersionedM2M(BaseVersionedObject):
    """ this abstract model is used as a connection between two objects for many 
    to many relationship for versioned objects instead of ManyToMany field. """
    objects = VersionedM2MManager()

    class Meta:
        abstract = True