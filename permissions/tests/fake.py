from django.db import models
from tastypie.resources import ModelResource
from tastypie import fields
from tastypie.authentication import SessionAuthentication
from permissions.authorization import BaseAuthorization

from state_machine.models import BaseGnodeObject
from permissions.models import BasePermissionsMixin
from state_machine.versioning.descriptors import VersionedForeignKey

from permissions.resource import PermissionsResourceMixin


# models -----------------------------------------------------------------------


class ACLFakeOwnedModel(BasePermissionsMixin, BaseGnodeObject):
    """ simple versioned model with permissions """
    test_attr = models.IntegerField()


class ACLFakeModel(BaseGnodeObject):
    """ simple versioned model """
    test_attr = models.IntegerField()
    test_str_attr = models.CharField(max_length=50, blank=True)
    test_ref = VersionedForeignKey(
        ACLFakeOwnedModel, blank=True, null=True, on_delete=models.SET_NULL
    )


# resources --------------------------------------------------------------------


class FakeResource(ModelResource):
    test_attr = fields.IntegerField(attribute='test_attr')

    class Meta:
        queryset = ACLFakeModel.objects.all()
        resource_name = 'fakemodel'
        authentication = SessionAuthentication()
        authorization = BaseAuthorization()


class FakeOwnedResource(PermissionsResourceMixin, ModelResource):
    test_attr = fields.IntegerField(attribute='test_attr')

    class Meta:
        queryset = ACLFakeOwnedModel.objects.all()
        resource_name = 'fakeownedmodel'
        authentication = SessionAuthentication()
        authorization = BaseAuthorization()
