import os
import urlparse

from django.conf.urls import url
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.http import HttpResponse
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from tastypie import fields, http
from tastypie.utils import trailing_slash
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

    def dehydrate(self, bundle):
        """ tastypie does not (?) support full URLs having hostname etc. This is
        a hack to make full URLs with http:// etc. """

        prefix = bundle.request.is_secure() and 'https' or 'http'
        base = '%s://%s' % (prefix, bundle.request.get_host())

        fresh_bundle = super(BaseGNodeResource, self).dehydrate(bundle)
        for k, v in fresh_bundle.data.items():
            if not isinstance(v, str) or v is None:
                continue
            if v.startswith('/api/'):
                fresh_bundle.data[k] = urlparse.urljoin(base, v)

        return fresh_bundle

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


class BaseFileResourceMixin(ModelResource):

    def dehydrate(self, bundle):
        """ converts output for every FileField into an URL (as defined in
        file_url_regex """

        fresh_bundle = super(BaseFileResourceMixin, self).dehydrate(bundle)
        all_fields = self.Meta.object_class._meta.local_fields
        file_fields = [f for f in all_fields if isinstance(f, models.FileField)]

        for f in file_fields:
            uri = fresh_bundle.data['resource_uri']
            fresh_bundle.data[f.name] = os.path.join(uri, f.name) + '/'

        return fresh_bundle

    def file_url_regex(self, resource_name):
        return r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/(?P<attr_name>\w[\w/-]*)%s$" % \
               (resource_name, trailing_slash())

    def prepend_urls(self):
        legacy_urls = super(BaseFileResourceMixin, self).prepend_urls()
        return legacy_urls + [
            url(
                self.file_url_regex(self._meta.resource_name),
                self.wrap_view('process_file'),
                name="api_%s_data" % self._meta.resource_name
            )
        ]

    # TODO implement different file response formats (HDF5, JSON, etc.)

    def process_file(self, request, **kwargs):
        """
        :param request:     incoming http request
        :param pk:          ID of the object that has file fields
        :param attr_name:   name of the attribute where the file is stored
        :return:            Http Response
        """
        attr_name = kwargs.pop('attr_name')

        if not request.method in ['GET', 'PUT']:
            return http.HttpMethodNotAllowed("Use GET or PUT to manage files")

        try:
            bundle = self.build_bundle(
                data={'pk': kwargs['pk']}, request=request
            )
            obj = self.cached_obj_get(
                bundle=bundle, **self.remove_api_resource_names(kwargs)
            )

        except ObjectDoesNotExist:
            return http.HttpGone()

        except MultipleObjectsReturned:
            return http.HttpMultipleChoices("More than one object found "
                                            "at this URL.")

        try:
            field = self.Meta.object_class._meta.get_field_by_name(attr_name)[0]

        except FieldDoesNotExist:
            return http.HttpBadRequest("Attribute %s does not exist" %
                                       attr_name)

        if not isinstance(field, models.FileField):
            return http.HttpBadRequest("Attribute %s is not a data-field" %
                                       attr_name)

        if request.method == 'GET':
            ffile = getattr(obj, attr_name)
            with open(ffile.path, 'r') as f:
                response = HttpResponse(f.read(), mimetype='application/x-hdf')
                response['Content-Disposition'] = "attachment; filename=%s" % \
                                                  os.path.basename(ffile.path)
                response['Content-Length'] = os.path.getsize(f.name)
                return response

        if not obj.is_editable(request.user):
            return http.HttpUnauthorized("No access to the update this object")

        if not len(request.FILES) > 0:
            return http.HttpNoContent()

        # take first file in the multipart/form request
        setattr(obj, attr_name, request.FILES.values()[0])
        obj.save()
        return http.HttpAccepted("File content updated successfully")