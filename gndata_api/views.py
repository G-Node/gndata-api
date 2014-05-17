from django.core.files import File
from django.core.files.uploadhandler import MemoryFileUploadHandler
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render_to_response
from django.http import HttpResponseBadRequest
from django.template import RequestContext
from django.utils import six
from django.db import transaction
from tastypie import http

from gndata_api.urls import METADATA_RESOURCES, EPHYS_RESOURCES

import simplejson as json
import uuid
import h5py
import os

RESOURCES = dict(METADATA_RESOURCES.items() + EPHYS_RESOURCES.items())
RESOURCE_SCHEMAS = dict(
    (name, resource.build_schema()) for name, resource in RESOURCES.items()
)


def list_view(request, resource_type):
    if not resource_type in RESOURCES.keys():
        message = "Objects of type %s are note supported." % resource_type
        return HttpResponseBadRequest(message)

    res = RESOURCES[resource_type]
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

    res = RESOURCES[resource_type]
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


@csrf_exempt
@transaction.atomic
def in_bulk(request):
    """
    Parses an uploaded HDF5 'Delta' file with new/changed objects tree and
     creates/updates the database using appropriate API Resources.

     Tests for this function are available only at the client side.

    :param request:     multipart/form-data request with 'raw_file' delta file
                        that contains objects to be saved
    :return             "top"-object as normal JSON response
    """
    def get_fk_field_names(model_name):
        schema = RESOURCE_SCHEMAS[model_name]
        fields = schema['fields']

        fk = lambda x: x['type'] == 'related' and x['related_type'] == 'to_one'
        return [k for k, v in fields.items() if fk(v)]

    def get_m2m_field_names(model_name):
        schema = RESOURCE_SCHEMAS[model_name]
        fields = schema['fields']

        to_many = lambda x: x['type'] == 'related' and x['related_type'] == 'to_many'
        return [k for k, v in fields.items() if to_many(v)]

    # always save file to disk by removing MemoryFileUploadHandler
    for handler in request.upload_handlers:
        if isinstance(handler, MemoryFileUploadHandler):
            request.upload_handlers.remove(handler)

    if not (request.method == 'POST' and len(request.FILES) > 0):
        return http.HttpBadRequest("Supporting only POST multipart/form-data"
                                      " requests with files")

    if not 'raw_file' in request.FILES:
        return http.HttpBadRequest("The name of the field should be "
                                      "'raw_file'")

    if not request.user.is_authenticated():
        return http.HttpUnauthorized("Must authorize before uploading")

    path = request.FILES['raw_file'].temporary_file_path()
    try:
        f = h5py.File(path, 'r')
    except IOError:
        return HttpResponseBadRequest("Uploaded file is not an HDF5 file")

    incoming_locations = f.keys()
    todo = []  # array of ids to process as an ordered sequence
    ids_map = {}  # map of the temporary IDs to the new IDs of created objects
    saved = []  # collector of processed objects

    # this loop sorts object tree as "breadth-first" sequence based on their
    # parent <- children relations
    while incoming_locations:
        location = incoming_locations[0]
        json_obj = json.loads(f[location]['json'].value)

        model_name = location.split('-')[4]  # FIXME make more robust
        fk_names = get_fk_field_names(model_name)
        m2m_names = get_m2m_field_names(model_name)

        parents = [v for k, v in json_obj.items() if k in fk_names]
        m2ms = [v for k, v in json_obj.items() if k in m2m_names]
        m2m_flat = [v for m2m in m2ms for v in m2m]

        match = lambda x: len([k for k in incoming_locations if k.split('-')[5] == x]) > 0

        if len([x for x in parents + m2m_flat if match(x)]) == 0:
            todo.append(location)
            incoming_locations.remove(location)
        else:
            incoming_locations.append(incoming_locations.pop(0))

    # this loop saves actual objects
    while todo:
        location = todo[0]
        group = f[location]
        json_obj = json.loads(group['json'].value)

        _, _, _, _, model_name, obj_id, _ = location.split('-')  # FIXME robust?
        fk_names = get_fk_field_names(model_name)
        m2m_names = get_m2m_field_names(model_name)

        # update parent IDs to the IDs of created objects
        to_update = [k for k in json_obj.keys() if k in fk_names]
        for name in to_update:
            value = json_obj[name]
            if value is not None and value.startswith('TEMP'):
                json_obj[name] = ids_map[value]

        # update m2m IDs to the IDs of created objects
        to_update = [k for k in json_obj.keys() if k in m2m_names]
        for name in to_update:
            m2m_list = json_obj[name]
            if m2m_list is not None:
                json_obj[name] = [ids_map[x] if x.startswith('TEMP') else x for x in m2m_list]

        res = RESOURCES[model_name]
        if obj_id.startswith('TEMP'):  # create new object
            bundle = res.build_bundle(request=request, data=json_obj)
            res_bundle = res.obj_create(bundle)

            ids_map[obj_id] = res_bundle.obj.local_id

        else:  # update object
            request_bundle = res.build_bundle(request=request)
            obj = res.obj_get(request_bundle, pk=obj_id)

            bundle = res.build_bundle(obj=obj, data=json_obj, request=request)
            res_bundle = res.obj_update(bundle)

        # update data fields. no need to check permissions as they must be
        # already validated with the object update
        data_fields = [k for k in group.keys() if not k == 'json']
        for name in data_fields:

            # dump array to disk
            filename = uuid.uuid1().hex + ".h5"
            path = os.path.join("/tmp", filename)  # FIXME get proper temppath

            with h5py.File(path) as temp_f:
                temp_f.create_dataset(name=obj_id, data=group[name].value)

            setattr(res_bundle.obj, name, File(open(path)))

        if len(data_fields) > 0:
            res_bundle.obj.save()

        saved.append((model_name, res_bundle.obj.local_id))
        todo.remove(location)

    model_name, obj_id = saved[0]  # return top object
    res = RESOURCES[model_name]
    bundle = res.build_bundle(request=request)
    obj = res.obj_get(bundle, pk=obj_id)
    res_bundle = res.build_bundle(obj=obj, request=request)
    response = http.HttpAccepted(res.serialize(
        None, res.full_dehydrate(res_bundle), 'application/json'
    ))

    return response