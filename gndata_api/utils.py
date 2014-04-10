from django.contrib.auth.models import User

import os
import urlparse
import string
import random


# this is base32hex alphabet, used to create unique IDs
alphabet = tuple(list('0123456789' + string.ascii_uppercase)[:32])


# TODO refactor out
def get_field_by_name(model, field_name):
    flds = [f for f in model._meta.local_fields + model._meta.local_many_to_many if \
            f.name == field_name]
    if flds: return flds[0]
    return None


# TODO refactor out
def get_type(obj_or_class):
    """ every object/class has a type equal as lowercase name of the class. """
    try:  # test if a class is given
        test = issubclass( obj_or_class, object ) # True if class is given
        return obj_or_class.__name__.lower()

    except TypeError: # object is given
        return obj_or_class.__class__.__name__.lower()


def split_time(**kwargs):
    """ extracts 'at_time' into separate dict """
    timeflt = {}
    if kwargs.has_key('at_time'):
        timeflt['at_time'] = kwargs.pop('at_time')
    return kwargs, timeflt


def pathlist(permalink):
    """ returns a list like ['metadata', 'section', 'HTOS5G16RL'] from a given
    permalink '/metadata/section/HTOS5G16RL' """
    base_url = urlparse.urlparse(permalink).path

    if base_url[0] == "/":
        base_url = base_url[1:]
    if len(base_url) > 1 and base_url[-1] == "/":
        base_url = base_url[0: -1]

    return [i for i in base_url.split("/") if i != ""]


def get_id_from_permalink(permalink):
    """ parses permalink and extracts ID of the object """
    return pathlist(permalink)[2]


def get_url_base(model):
    """ returns a base part of the URL for a model, e.g. /metadata/section/
    for Section model. TODO: find a cleaner way to do that. """
    temp = model()
    if model == User: # not to break HTML interface
        return '/user/'
    setattr(temp, 'pk', 1)
    try:
        url = temp.get_absolute_url()
    except AttributeError:
        return '/'

    plst = pathlist(url)
    return "/" + plst[0] + "/" + plst[1] + "/"


def get_host_for_permalink( request ):
    return '%s://%s' % (request.is_secure() and 'https' or 'http', request.get_host())


def build_obj_location(model, id):
    """ build unique object location, like '/metadata/section/HTOS5G16RL' """
    if hasattr(model, 'base32str'):
        try: # id could be both string or int
            int(id)
            id = model.base32str(id)

        except ValueError:
            pass

    id = str(id) # make sure type is string, for objects like user
    url_base = get_url_base(model)
    return os.path.join(url_base, id) + '/'


def base32str(value):
    """ converts base32 integer into the string """
    result = ''
    mask = 31
    while value > 0:
        result = alphabet[ value & mask ] + result
        value = value >> 5
    return result


def base32int(value):
    """ converts base32 string into integer """
    return int(value, 32)


def get_new_local_id():
    """ new 10-chars base32 ID, unique between different object versions """
    uid = random.choice(alphabet[1:])
    for i in range(9):
        uid += random.choice(alphabet)
    return base32int(uid)