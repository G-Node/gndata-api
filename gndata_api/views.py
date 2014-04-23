from django.shortcuts import render_to_response
from django.http import HttpResponseBadRequest
from django.template import RequestContext
from django.utils import six

from metadata.api import *
from ephys.api import *

import simplejson as json


RESOURCES = {
    'document': DocumentResource,
    'section': SectionResource,
    'property': PropertyResource,
    'value': ValueResource,
    'block': BlockResource,
    'segment': SegmentResource,
    'eventarray': EventArrayResource,
    'event': EventResource,
    'epocharray': EpochArrayResource,
    'epoch': EpochResource,
    'recordingchannelgroup': RCGResource,
    'recordingchannel': RCResource,
    'unit': UnitResource,
    'spiketrain': SpikeTrainResource,
    'analogsignalarray': ASAResource,
    'analogsignal': AnalogSignalResource,
    'irregularlysampledsignal': IRSAResource,
    'spike': SpikeResource,
}


def list_view(request, resource_type):
    if not resource_type in RESOURCES.keys():
        message = "Objects of type %s are note supported." % resource_type
        return HttpResponseBadRequest(message)

    res = RESOURCES[resource_type]()
    request_bundle = res.build_bundle(request=request)
    queryset = res.obj_get_list(request_bundle)

    schema = res.build_schema()

    content = {
        'obj_list': queryset,
        'resource_type': resource_type,
        'schema': schema
    }
    return render_to_response('list_view.html', content,
                              context_instance=RequestContext(request))


def detail_view(request, resource_type, id):

    def get_related_objs(resource, field_name, bundle):
        """ field name should be of 'related' type """
        attribute = getattr(resource, field_name).attribute

        if isinstance(attribute, six.string_types):
            return getattr(bundle.obj, attribute, None)

        elif callable(attribute):
            return attribute(bundle)

    if not resource_type in RESOURCES.keys():
        message = "Objects of type %s are note supported." % resource_type
        return HttpResponseBadRequest(message)

    res = RESOURCES[resource_type]()
    request_bundle = res.build_bundle(request=request)
    obj = res.obj_get(request_bundle, pk=id)

    bundle = res.build_bundle(obj=obj, request=request)
    res.full_dehydrate(bundle, for_list=True)

    obj_as_json = json.loads(res.serialize(None, bundle, "application/json"))

    schema = res.build_schema()
    fields = schema['fields']

    # parsing standard attributes for rendering
    normal = lambda x: x['type'] != 'related'
    normal_names = [k for k, v in fields.items() if normal(v)]
    normal_fields = dict([(k, v) for k, v in obj_as_json.items()
                          if k in normal_names])

    # parsing FK fields for rendering
    to_one = lambda x: x['type'] == 'related' and x['related_type'] == 'to_one'
    to_one_names = [k for k, v in fields.items() if to_one(v)]
    to_one_fields = dict([(n, getattr(obj, n)) for n in to_one_names
                          if getattr(obj, n) is not None])

    # parsing reversed relationships for rendering
    to_many = lambda x: x['type'] == 'related' and x['related_type'] == 'to_many'
    to_many_names = [k for k, v in fields.items() if to_many(v)]
    to_many_fields = {}
    for n in to_many_names:
        qs = get_related_objs(res, n, bundle).all()
        if len(qs) > 0:
            to_many_fields[qs.model.__name__.lower()] = qs

    content = {
        'obj': obj,
        'resource_type': resource_type,
        'normal_fields': normal_fields,
        'to_one_fields': to_one_fields,
        'to_many_fields': to_many_fields
    }
    return render_to_response('detail_view.html', content,
                              context_instance=RequestContext(request))