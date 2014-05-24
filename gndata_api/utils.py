from django.contrib.auth.models import User

import os
import urlparse
import string
import random

from django.core.management.color import no_style
from django.db import connection, models
from gndata_api import settings

# this is base32hex alphabet, used to create unique IDs
alphabet = tuple(list('0123456789' + string.ascii_uppercase)[:32])


def get_simple_field_names(model):
    filt = lambda x: not issubclass(x, models.ForeignKey) and \
                     not issubclass(x, models.FileField)
    return [f.name for f in model._meta.local_fields() if filt(f)]


def get_fk_field_names(model):
    filt = lambda x: issubclass(x, models.ForeignKey)
    return [f.name for f in model._meta.local_fields() if filt(f)]


def get_m2m_field_names(model):
    return [f.name for f in model._meta.local_m2m_fields()]


def get_data_field_names(model):
    filt = lambda x: issubclass(x, models.FileField)
    return [f for f in model._meta.local_fields() if filt(f)]


def get_reverse_models(model):
    return [f.model for f in model._meta.m1.get_all_related_objects()]


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
    return uid


#===============================================================================
# these methods create / delete tables for fake models. Actually unittest does
# the creation itself, so create_fake_model() and delete_fake_model() methods
# are not used
#===============================================================================


def update_keys_for_model(model):
    """ Versioned models need to have changes in the DB schema, in particular
    the PK should be changed from 'local_id' to the 'guid' """
    sql = []
    db_table = model._meta.db_table
    engine = settings.DATABASES['default']['ENGINE']

    if engine == 'django.db.backends.postgresql_psycopg2':
        sql.append(''.join(["ALTER TABLE ", db_table, " DROP CONSTRAINT ", db_table, "_pkey"]))
        sql.append(''.join(["ALTER TABLE ", db_table, " ADD PRIMARY KEY (guid)"]))

    elif engine == 'django.db.backends.mysql':
        sql.append(''.join(["ALTER TABLE `", db_table, "` DROP PRIMARY KEY;"]))
        sql.append(''.join(["ALTER TABLE `", db_table, "` ADD PRIMARY KEY (`guid`);"]))

    else:
        raise TypeError('The current database engine is not supported.')

    _cursor = connection.cursor()
    for statement in sql:
        _cursor.execute(statement)


def create_fake_model(prototype):
    """ Create the schema for the versioned prototype model """
    sql, _ = connection.creation.sql_create_model(prototype, no_style())
    _cursor = connection.cursor()
    for statement in sql:
        _cursor.execute(statement)

    # versioned objects require PRIMARY KEY change
    update_keys_for_model(prototype)


def delete_fake_model(model):
    """ Delete the schema for the test model """
    sql = connection.creation.sql_destroy_model(model, (), no_style())
    _cursor = connection.cursor()
    for statement in sql:
        _cursor.execute(statement)