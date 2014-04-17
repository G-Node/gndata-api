from tastypie.resources import ModelResource, ALL
from tastypie.authentication import SessionAuthentication
from permissions.models import SingleAccess
from permissions.authorization import ACLManageAuthorization


class ACLResource(ModelResource):
    class Meta:
        queryset = SingleAccess.objects.all()
        resource_name = 'acl'
        filtering = {
            'object_id': ALL,
            'object_type': ALL,
            'access_for': ALL,
            'access_level': ALL
        }
        authentication = SessionAuthentication()
        authorization = ACLManageAuthorization()