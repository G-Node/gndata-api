from django.db import models

from state_machine.models import BaseGnodeObject
from state_machine.versioning.models import VersionedM2M
from state_machine.versioning.descriptors import VersionedForeignKey
from state_machine.versioning.descriptors import VersionedManyToManyField

#===============================================================================
# Fake but "instantiatable" classes are defined here to TEST abstract classes
# for state_machine models
#===============================================================================


class FakeModel(BaseGnodeObject):
    """ simple versioned model """
    test_attr = models.IntegerField()
    test_str_attr = models.CharField(max_length=50, blank=True)


class FakeParentModel(BaseGnodeObject):
    """ versioned model with M2M relationship and reverse FK relationship """
    test_attr = models.IntegerField()
    m2m = VersionedManyToManyField(
        FakeModel, through='parent_fake', blank=True, null=True
    )


class FakeChildModel(BaseGnodeObject):
    """ simple versioned model with parent """
    test_attr = models.IntegerField()
    test_ref = VersionedForeignKey(
        FakeParentModel, blank=True, null=True, on_delete=models.SET_NULL
    )


class parent_fake(VersionedM2M):
    """ M2M relationship class """
    parent = VersionedForeignKey(FakeParentModel)
    fake = VersionedForeignKey(FakeModel)