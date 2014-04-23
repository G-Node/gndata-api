from django.conf.urls import url
from django.http import HttpResponse
from tastypie.resources import Resource, ModelResource
from tastypie.utils import trailing_slash
from tastypie import fields
from tastypie.authentication import SessionAuthentication
from tastypie.resources import ALL

from permissions.authorization import ACLManageAuthorization
from permissions.models import SingleAccess
from account.api import UserResource
from rest.resource import get_object_or_response


class ACLResource(ModelResource):
    user = fields.ForeignKey(UserResource, attribute='access_for')

    class Meta:
        queryset = SingleAccess.objects.all()
        resource_name = 'acl'
        authentication = SessionAuthentication()
        authorization = ACLManageAuthorization()
        filtering = {
            'object_id': ALL,
            'object_type': ALL
        }
        fields = ['access_level']

    def obj_get_list(self, bundle, **kwargs):
        keys = kwargs.keys()
        if not 'object_id' in keys or not 'object_type' in keys:
            raise ValueError('Must have type and ID to manage permissions')

        return super(ACLResource, self).obj_get_list(bundle, **kwargs)


class PermissionsResourceMixin(Resource):
    """ prototype """

    def prepend_urls(self):
        return [
            url(
                r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/acl%s$" % \
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('process_permissions'),
                name="api_process_permissions"
            )
        ]

    def process_permissions(self, request, **kwargs):
        pk = kwargs.pop('pk')
        obj = get_object_or_response(self, request, pk, **kwargs)
        if isinstance(obj, HttpResponse):
            return obj

        acl_resource = ACLResource()

        if request.method == 'PUT':
            new_accesses = acl_resource.deserialize(request, request.body)

            update = {}
            user_resource = UserResource()
            for access in new_accesses:
                clean_user = user_resource.get_via_uri(access['user'])
                update[clean_user.pk] = access['access_level']

            obj.share(update)

        # possible option without resource
        #qs = SingleAccess.objects.filter(**params)
        #format = determine_format(request, ser, "application/json")
        #ser.serialize(qs, format)

        params = {
            'object_id': obj.pk,
            'object_type': obj.acl_type
        }
        request_bundle = acl_resource.build_bundle(request=request)

        bundles = []
        for access in acl_resource.obj_get_list(request_bundle, **params):
            bundle = acl_resource.build_bundle(obj=access, request=request)
            bundles.append(acl_resource.full_dehydrate(bundle, for_list=True))

        return acl_resource.create_response(request, bundles)