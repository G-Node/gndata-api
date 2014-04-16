from tastypie.resources import ALL, ALL_WITH_RELATIONS
from tastypie import fields
from tastypie.authentication import SessionAuthentication

from rest.authorization import BaseAuthorization
from rest.resource import BaseModelResource
from metadata.models import Document, Section, Property, Value


class DocumentResource(BaseModelResource):

    class Meta:
        queryset = Document.objects.all()
        resource_name = 'document'
        excludes = ['starts_at', 'ends_at']
        filtering = {
            'author': ALL,
            'date': ALL,
            'version': ALL,
            'repository': ALL,
            'owner': ALL_WITH_RELATIONS
        }
        authentication = SessionAuthentication()
        authorization = BaseAuthorization()


class SectionResource(BaseModelResource):
    document = fields.ForeignKey(DocumentResource, 'document')
    section = fields.ToOneField('self', 'section', blank=True, null=True)
    section_set = fields.ToManyField(
        'metadata.api.SectionResource', 'section_set', related_name='section',
        full=False, blank=True, null=True
    )  # FIXME always empty
    property_set = fields.ToManyField(
        'metadata.api.PropertyResource', 'property_set', related_name='section',
        full=False, blank=True, null=True
    )

    class Meta:
        queryset = Section.objects.all()
        resource_name = 'section'
        excludes = ['starts_at', 'ends_at']
        filtering = {
            'name': ALL,
            'type': ALL,
            'reference': ALL,
            'definition': ALL,
            'link': ALL,
            'include': ALL,
            'repository': ALL,
            'mapping': ALL,
            'section': ALL_WITH_RELATIONS,
            'owner': ALL_WITH_RELATIONS
        }
        authentication = SessionAuthentication()
        authorization = BaseAuthorization()


class PropertyResource(BaseModelResource):
    section = fields.ToOneField(SectionResource, 'section')

    class Meta:
        queryset = Property.objects.all()
        resource_name = 'property'
        excludes = ['starts_at', 'ends_at']
        filtering = {
            'name': ALL,
            'definition': ALL,
            'mapping': ALL,
            'dependency': ALL,
            'dependencyvalue': ALL,
            'section': ALL_WITH_RELATIONS,
            'owner': ALL_WITH_RELATIONS
        }
        authentication = SessionAuthentication()
        authorization = BaseAuthorization()


class ValueResource(BaseModelResource):
    property = fields.ForeignKey(PropertyResource, 'property')

    class Meta:
        queryset = Value.objects.all()
        resource_name = 'value'
        excludes = ['starts_at', 'ends_at']
        filtering = {
            'type': ALL,
            'uncertainty': ALL,
            'unit': ALL,
            'definition': ALL,
            'filename': ALL,
            'encoder': ALL,
            'checksum': ALL,
            'property': ALL_WITH_RELATIONS,
            'owner': ALL_WITH_RELATIONS
        }
        authentication = SessionAuthentication()
        authorization = BaseAuthorization()