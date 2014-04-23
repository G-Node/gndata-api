from tastypie.resources import ALL, ALL_WITH_RELATIONS
from tastypie import fields
from tastypie.authentication import SessionAuthentication
from permissions.authorization import BaseAuthorization
from permissions.resource import BaseGNodeResource

from ephys.models import *


class BlockResource(BaseGNodeResource):
    #block_set = fields.ToManyField(
    #    'ephys.api.SegmentResource', 'segment_set', related_name='block',
    #    full=False, blank=True, null=True
    #)

    class Meta:
        queryset = Block.objects.all()
        resource_name = 'block'
        excludes = ['starts_at', 'ends_at']
        filtering = {
            'local_id': ALL,
            'name': ALL,
            'description': ALL,
            'filedatetime': ALL,
            'index': ALL,
            'owner': ALL_WITH_RELATIONS
        }
        authentication = SessionAuthentication()
        authorization = BaseAuthorization()