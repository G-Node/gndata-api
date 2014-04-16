from django.db import models
from django.db import connection
from django.core.management.color import no_style
from gndata_api import settings

from state_machine.models import BaseGnodeObject, BaseGnodeObjectWithACL
from state_machine.versioning.models import VersionedM2M
from state_machine.versioning.descriptors import VersionedForeignKey
from state_machine.versioning.descriptors import VersionedManyToManyField


#===============================================================================
# Fake but "instantiatable" classes are defined here to TEST abstract classes
# for state_machine models
#===============================================================================


class FakeModel(BaseGnodeObject):
    """ simple versioned model """
    test_attr = models.IntegerField()
    test_str_attr = models.CharField(max_length=50, blank=True)


class FakeParentModel(BaseGnodeObject):
    """ versioned model with M2M relationship and reverse FK relationship """
    test_attr = models.IntegerField()
    m2m = VersionedManyToManyField(
        FakeModel, through='parent_fake', blank=True, null=True
    )


class FakeChildModel(BaseGnodeObject):
    """ simple versioned model with parent """
    test_attr = models.IntegerField()
    test_ref = VersionedForeignKey(
        FakeParentModel, blank=True, null=True, on_delete=models.SET_NULL
    )


class parent_fake(VersionedM2M):
    """ M2M relationship class """
    parent = VersionedForeignKey(FakeParentModel)
    fake = VersionedForeignKey(FakeModel)


class FakeOwnedModel(BaseGnodeObjectWithACL):
    """ simple versioned model with permissions """
    test_attr = models.IntegerField()


#===============================================================================
# these methods create / delete tables for fake models. Actually unittest does
# the creation itself, so create_fake_model() and delete_fake_model() methods
# are not used
#===============================================================================


def create_fake_model(prototype):
    """ Create the schema for our prototype model """
    sql, _ = connection.creation.sql_create_model(prototype, no_style())
    _cursor = connection.cursor()
    for statement in sql:
        _cursor.execute(statement)
    # versioned objects require PRIMARY KEY change
    if issubclass(prototype, BaseGnodeObject):
        update_keys_for_model(prototype)


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


def delete_fake_model(model):
    """ Delete the schema for the test model """
    sql = connection.creation.sql_destroy_model(model, (), no_style())
    _cursor = connection.cursor()
    for statement in sql:
        _cursor.execute(statement)