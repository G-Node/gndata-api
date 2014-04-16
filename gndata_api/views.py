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
        'objects': queryset,
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

    obj_as_json = res.serialize(None, bundle, "application/json")

    content = {
        'obj': obj,
        'resource_type': resource_type,
        'obj_as_json': json.loads(obj_as_json)
    }
    return render_to_response('detail_view.html', content)