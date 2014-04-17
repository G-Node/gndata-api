from django.conf.urls import url
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from tastypie.resources import ModelResource
from tastypie.utils import trailing_slash
from tastypie import http


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

        # TODO
        # acl_resource = ACLResource()
        # acl_resource.get_list(request, local_id=obj.pk, acl_type=obj.acl_type)
        return http.HttpNoContent()