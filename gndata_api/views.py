from django.shortcuts import render_to_response
from django.http import HttpResponseBadRequest

from metadata.api import *
from gndata_api.utils import base32int

import simplejson as json


RESOURCES = {
    'document': DocumentResource,
    'section': SectionResource,
    'property': PropertyResource,
    'value': ValueResource
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
    return render_to_response('list_view.html', content)


def detail_view(request, resource_type, id):
    if not resource_type in RESOURCES.keys():
        message = "Objects of type %s are note supported." % resource_type
        return HttpResponseBadRequest(message)

    res = RESOURCES[resource_type]()
    request_bundle = res.build_bundle(request=request)
    obj = res.obj_get(request_bundle, pk=base32int(id))

    bundle = res.build_bundle(obj=obj, request=request)
    res.full_dehydrate(bundle, for_list=True)

    obj_as_json = json.loads(res.serialize(None, bundle, "application/json"))

    schema = res.build_schema()
    fields = schema['fields']

    normal = lambda x: x['type'] != 'related'
    normal_names = [k for k, v in fields.items() if normal(v)]
    normal_fields = dict([(k, v) for k, v in obj_as_json.items()
                          if k in normal_names])

    to_one = lambda x: x['type'] == 'related' and x['related_type'] == 'to_one'
    to_one_names = [k for k, v in fields.items() if to_one(v)]
    to_one_fields = dict([(n, getattr(obj, n)) for n in to_one_names
                          if getattr(obj, n) is not None])

    to_many = lambda x: x['type'] == 'related' and x['related_type'] == 'to_many'
    to_many_names = [k for k, v in fields.items() if to_many(v)]
    to_many_fields = {}
    for n in to_many_names:
        qs = getattr(obj, n).all()
        if len(qs) > 0:
            to_many_fields[qs.model.__name__.lower()] = qs

    content = {
        'obj': obj,
        'resource_type': resource_type,
        'normal_fields': normal_fields,
        'to_one_fields': to_one_fields,
        'to_many_fields': to_many_fields
    }
    return render_to_response('detail_view.html', content)