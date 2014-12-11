import os
import urlparse

from django.conf.urls import url
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.http import HttpResponse
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from tastypie import fields, http
from tastypie.utils import trailing_slash
from tastypie.constants import ALL, ALL_WITH_RELATIONS
from tastypie.resources import ModelResource
from account.api import UserResource
from permissions.authorization import BaseAuthorization
from permissions.authorization import SessionAuthenticationNoSCRF


class BaseMeta(object):
    """ An abstract Meta class to set several common attributes to Resource
    objects """

    excludes = ['starts_at', 'ends_at']
    authentication = SessionAuthenticationNoSCRF()
    authorization = BaseAuthorization()
    collection_name = 'selected'
    always_return_data = True
    filtering = {
        'id': ALL,
        'date_created': ALL,
        'owner': ALL_WITH_RELATIONS
    }

    @property
    def resource_name(self):
        return self.object_class.__name__.lower()

    @property
    def filtering(self):
        local = self.object_class._meta.local_fields
        fields = [f for f in local if f.name not in ['starts_at', 'ends_at']]

        get_filter = lambda field: ALL_WITH_RELATIONS if \
            isinstance(field, models.ForeignKey) else ALL

        filters = dict([(field.name, get_filter(field)) for field in fields])
        if 'local_id' in filters.keys():
            filters['id'] = filters.pop('local_id')

        return filters


class BaseGNodeResource(ModelResource):

    owner = fields.ForeignKey(UserResource, 'owner', readonly=True)
    date_created = fields.DateTimeField(attribute='date_created', readonly=True)
    guid = fields.CharField(attribute='guid', readonly=True)
    id = fields.CharField(attribute='local_id', readonly=True)

    def determine_format(self, request):
        return 'application/json'

    def dehydrate(self, bundle):
        """ tastypie does not (?) support full URLs having hostname etc. This is
        a hack to make full URLs with http:// etc. """
        def extend_if_url(sample):
            if sample.startswith('/api/'):
                return urlparse.urljoin(base, sample)
            return sample

        prefix = bundle.request.is_secure() and 'https' or 'http'
        base = '%s://%s' % (prefix, bundle.request.get_host())

        fresh_bundle = super(BaseGNodeResource, self).dehydrate(bundle)

        for k, v in fresh_bundle.data.copy().items():
            if k == 'resource_uri':  # add location
                fresh_bundle.data['location'] = v

            elif isinstance(v, basestring):
                fresh_bundle.data[k] = extend_if_url(v)

            elif isinstance(v, list):
                fresh_bundle.data[k] = [extend_if_url(x) for x in v]

        return fresh_bundle

    def hydrate(self, bundle):
        """ convert given full URLs (with http:// etc.) and single IDs for
        related FK fields into standard API form like /api/v1/<resource>/<id>/
        """
        def normalize_if_url(value):
            # check if full URL is given
            if value.lower().startswith("http"):
                return urlparse.urlparse(value).path

            # check if just an ID is given
            elif not value.lower().startswith("/api/"):
                to = field.to_class
                return "/api/v1/%s/%s/%s/" % (  # FIXME generalize URL prefix
                    to._meta.api_name, to._meta.resource_name, value
                )
            return value

        fresh_bundle = super(BaseGNodeResource, self).hydrate(bundle)

        is_related = lambda x: hasattr(x, 'is_related') and x.is_related
        rel_fields = [(n, f) for n, f in self.fields.items() if is_related(f)]
        for name, field in rel_fields:
            if not name in fresh_bundle.data.keys():
                continue

            value = fresh_bundle.data[name]
            if isinstance(value, basestring):
                fresh_bundle.data[name] = normalize_if_url(value)

            elif isinstance(value, list):
                fresh_bundle.data[name] = [normalize_if_url(x) for x in value]

        return fresh_bundle

    def obj_create(self, bundle, **kwargs):
        """ always set owner of an object to the request.user """
        return super(BaseGNodeResource, self).obj_create(
            bundle, owner=bundle.request.user
        )

    def save_m2m(self, bundle):
        """ ignore m2m relations sent via the API. TODO add specific m2m like
        for RCG <-> RC and others, if any """
        pass

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

    def __init__(self, *args, **kwargs):
        """ makes all file fields read-only to avoid parsing these fields on
        create / update """
        super(BaseFileResourceMixin, self).__init__(*args, **kwargs)
        for name, field in self.file_fields.items():
            field.readonly = True

    def dehydrate(self, bundle):
        """ converts output for every FileField into an URL (as defined in
        file_url_regex """

        fresh_bundle = super(BaseFileResourceMixin, self).dehydrate(bundle)

        for name, field in self.file_fields.items():
            uri = fresh_bundle.data['resource_uri']
            fresh_bundle.data[name] = os.path.join(uri, name) + '/'

        return fresh_bundle

    @property
    def file_fields(self):
        return dict([(name, field) for name, field in self.fields.items()
                     if isinstance(field, fields.FileField)])

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

        if not request.method in ['GET', 'POST']:
            return http.HttpMethodNotAllowed("Use GET or POST to manage files")

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
            field = self._meta.object_class._meta.get_field_by_name(attr_name)[0]

        except FieldDoesNotExist:
            return http.HttpBadRequest("Attribute %s does not exist" %
                                       attr_name)

        if not isinstance(field, models.FileField):
            return http.HttpBadRequest("Attribute %s is not a data-field" %
                                       attr_name)

        if request.method == 'GET':
            ffile = getattr(obj, attr_name)
            try:
                filepath = ffile.path
            except ValueError:  # file is not set, empty
                return http.HttpNoContent()

            with open(filepath, 'r') as f:
                response = HttpResponse(f.read(), content_type='application/x-hdf')
                response['Content-Disposition'] = "attachment; filename=%s" % \
                                                  os.path.basename(filepath)
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
