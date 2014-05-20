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
    block_set = fields.ToManyField(
        'ephys.api.BlockResource', 'block_set', related_name='section',
        full=False, blank=True, null=True
    )
    segment_set = fields.ToManyField(
        'ephys.api.SegmentResource', 'segment_set', related_name='section',
        full=False, blank=True, null=True
    )

    class Meta(BaseMeta):
        queryset = Section.objects.all()


class PropertyResource(BaseGNodeResource):
    section = fields.ToOneField(SectionResource, 'section')
    value_set = fields.ToManyField(
        'metadata.api.ValueResource', 'value_set', related_name='property',
        full=False, blank=True, null=True
    )

    class Meta(BaseMeta):
        queryset = Property.objects.all()
        excludes = ['starts_at', 'ends_at', 'document']


class ValueResource(BaseGNodeResource):
    property = fields.ForeignKey(PropertyResource, 'property')

    class Meta(BaseMeta):
        queryset = Value.objects.all()
        excludes = ['starts_at', 'ends_at', 'document']