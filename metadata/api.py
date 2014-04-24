from tastypie.resources import ALL, ALL_WITH_RELATIONS
from tastypie import fields

from metadata.models import Document, Section, Property, Value
from rest.resource import BaseGNodeResource, BaseMeta
from permissions.resource import PermissionsResourceMixin


class DocumentResource(BaseGNodeResource, PermissionsResourceMixin):
    section_set = fields.ToManyField(
        'metadata.api.SectionResource', attribute=lambda bundle:
        Section.objects.filter(document=bundle.obj, section__isnull=True),
        related_name='document',
        full=False, blank=True, null=True
    )

    class Meta(BaseMeta):
        queryset = Document.objects.all()
        resource_name = 'document'
        filtering = {
            'author': ALL,
            'date': ALL,
            'version': ALL,
            'repository': ALL,
            'owner': ALL_WITH_RELATIONS,
            'local_id': ALL,
            'date_created': ALL
        }


class SectionResource(BaseGNodeResource):
    document = fields.ForeignKey(DocumentResource, 'document')
    section = fields.ToOneField('self', 'section', blank=True, null=True)
    section_set = fields.ToManyField(
        'metadata.api.SectionResource', 'section_set', related_name='section',
        full=False, blank=True, null=True
    )
    property_set = fields.ToManyField(
        'metadata.api.PropertyResource', 'property_set', related_name='section',
        full=False, blank=True, null=True
    )

    class Meta(BaseMeta):
        queryset = Section.objects.all()
        resource_name = 'section'
        filtering = {
            'local_id': ALL,
            'name': ALL,
            'type': ALL,
            'reference': ALL,
            'definition': ALL,
            'link': ALL,
            'include': ALL,
            'repository': ALL,
            'mapping': ALL,
            'section': ALL_WITH_RELATIONS,
            'owner': ALL_WITH_RELATIONS,
            'date_created': ALL
        }


class PropertyResource(BaseGNodeResource):
    section = fields.ToOneField(SectionResource, 'section')
    value_set = fields.ToManyField(
        'metadata.api.ValueResource', 'value_set', related_name='property',
        full=False, blank=True, null=True
    )

    class Meta(BaseMeta):
        queryset = Property.objects.all()
        resource_name = 'property'
        excludes = ['starts_at', 'ends_at', 'document']
        filtering = {
            'name': ALL,
            'definition': ALL,
            'mapping': ALL,
            'dependency': ALL,
            'dependencyvalue': ALL,
            'section': ALL_WITH_RELATIONS,
            'owner': ALL_WITH_RELATIONS,
            'local_id': ALL,
            'date_created': ALL
        }


class ValueResource(BaseGNodeResource):
    property = fields.ForeignKey(PropertyResource, 'property')

    class Meta:
        queryset = Value.objects.all()
        resource_name = 'value'
        excludes = ['starts_at', 'ends_at', 'document']
        filtering = {
            'type': ALL,
            'uncertainty': ALL,
            'unit': ALL,
            'definition': ALL,
            'filename': ALL,
            'encoder': ALL,
            'checksum': ALL,
            'property': ALL_WITH_RELATIONS,
            'owner': ALL_WITH_RELATIONS,
            'local_id': ALL,
            'date_created': ALL
        }