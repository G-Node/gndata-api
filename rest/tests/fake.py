from django.db import models

from state_machine.models import BaseGnodeObject
from permissions.models import BasePermissionsMixin

#===============================================================================
# Fake but "instantiatable" classes are defined here to TEST abstract classes
# for state_machine models
#===============================================================================


class RestFakeModel(BaseGnodeObject):
    """ simple versioned model """
    test_attr = models.IntegerField()
    test_str_attr = models.CharField(max_length=50, blank=True)


class RestFakeOwnedModel(BasePermissionsMixin, BaseGnodeObject):
    """ simple versioned model with permissions """
    test_attr = models.IntegerField()