from django.conf.urls import url
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from tastypie.resources import Resource, ModelResource
from tastypie.utils import trailing_slash
from tastypie import http, fields
from tastypie import fields
from tastypie.authentication import SessionAuthentication
from tastypie.resources import ALL

from permissions.authorization import ACLManageAuthorization
from permissions.models import SingleAccess
from account.api import UserResource


class BaseGNodeResource(ModelResource):

    owner = fields.ForeignKey(UserResource, 'owner')

    def get_schema(self, request, **kwargs):
        """
        Returns a serialized form of the schema of the resource.

        This method is overloaded as the superclass method uses dummy (empty)
        object together with the 'authorized_read_detail' method to check for
        access to the schema, which fails as the owner for the empty object is
        obviously not set.

        Should return a HttpResponse (200 OK).
        """
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)
        self.log_throttled_access(request)
        return self.create_response(request, self.build_schema())


class ACLResource(ModelResource):
    user = fields.ForeignKey(UserResource, attribute='access_for')
    level = fields.IntegerField(attribute='access_level', default=1)

    class Meta:
        queryset = SingleAccess.objects.all()
        resource_name = 'acl'
        authentication = SessionAuthentication()
        authorization = ACLManageAuthorization()
        filtering = {
            'object_id': ALL,
            'object_type': ALL
        }

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
        try:
            bundle = self.build_bundle(data={'pk': kwargs['pk']}, request=request)
            obj = self.cached_obj_get(bundle=bundle, **self.remove_api_resource_names(kwargs))

        except ObjectDoesNotExist:
            return http.HttpGone()

        except MultipleObjectsReturned:
            return http.HttpMultipleChoices("More than one resource is found at this URI.")

        if not obj.owner.pk == request.user.pk:
            return http.HttpForbidden("No access to the ACL of this object")

        if not request.method in ['GET', 'PUT']:
            return http.HttpMethodNotAllowed("Use GET or PUT to manage permissions")

        acl_resource = ACLResource()

        if request.method == 'PUT':
            users = acl_resource.deserialize(request, request.PUT.data)
            import ipdb
            ipdb.set_trace()

            obj.share(users)

        # possible option without resource
        #qs = SingleAccess.objects.filter(**params)
        #format = determine_format(request, ser, "application/json")
        #ser.serialize(qs, format)

        params = {
            'object_id': obj.pk,
            'object_type': obj.acl_type
        }
        request_bundle = acl_resource.build_bundle(request=request)
        data = acl_resource.obj_get_list(request_bundle, **params)
        return acl_resource.create_response(request, data)