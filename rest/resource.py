import os

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.http import HttpResponse
from django import forms
from tastypie import fields, http
from tastypie.authentication import SessionAuthentication
from tastypie.constants import ALL, ALL_WITH_RELATIONS
from tastypie.resources import ModelResource
from account.api import UserResource
from permissions.authorization import BaseAuthorization


class BaseMeta:
    excludes = ['starts_at', 'ends_at']
    authentication = SessionAuthentication()
    authorization = BaseAuthorization()
    filtering = {
        'local_id': ALL,
        'owner': ALL_WITH_RELATIONS
    }


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


def get_object_or_response(resource, request, pk, **kwargs):
    try:
        bundle = resource.build_bundle(data={'pk': pk}, request=request)
        obj = resource.cached_obj_get(bundle=bundle, **resource.remove_api_resource_names(kwargs))

    except ObjectDoesNotExist:
        return http.HttpGone()

    except MultipleObjectsReturned:
        return http.HttpMultipleChoices("More than one resource is found at this URI.")

    if not obj.owner.pk == request.user.pk:
        return http.HttpUnauthorized("No access to the ACL of this object")

    if not request.method in ['GET', 'PUT']:
        return http.HttpMethodNotAllowed("Use GET or PUT to manage permissions")

    return obj


# TODO implement different file response formats (HDF5, JSON, etc.)

def process_file(resource, request, pk, attr_name, **kwargs):
    """
    :param resource:    REST resource of the appropriate model
    :param request:     incoming http request
    :param pk:          ID of the object that has file fields
    :param attr_name:   name of the attribute where the file is stored
    :return:            Http Response
    """
    class FileForm(forms.Form):
        raw_file = forms.FileField()

    if not request.method in ['GET', 'PUT']:
        return http.HttpMethodNotAllowed("Use GET or PUT to manage files")

    obj = get_object_or_response(resource, request, pk)
    if isinstance(obj, HttpResponse):
        return obj

    if request.method == 'GET':
        with getattr(obj, attr_name).open() as f:
            response = HttpResponse(f.read(), mimetype='application/x-hdf')
            response['Content-Disposition'] = 'attachment; filename=%s.h5' % f.name
            response['Content-Length'] = os.path.getsize(f.name)
            return response

    if not len(request.FILES) > 0:
        return http.HttpNoContent()

    form = FileForm(request.FILES)
    if form.is_valid():
        import ipdb
        ipdb.set_trace()

        setattr(obj, attr_name, form.raw_file)

        return http.HttpAccepted('File content updated successfully')

    else:
        return http.HttpBadRequest(form.errors)
