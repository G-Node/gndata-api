from django.conf.urls import url
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from tastypie.resources import ModelResource
from tastypie.utils import trailing_slash
from tastypie import http
from permissions.api import ACLResource


class PermissionsResourceMixin(ModelResource):
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

        acl_resource = ACLResource()
        if request.GET:
            request.GET['object_id'] = obj.pk
            request.GET['object_type'] = obj.acl_type
            return acl_resource.obj_get_list(request)

        elif request.PUT:
            pass

        return http.HttpMethodNotAllowed("Use GET or PUT to manage permissions")