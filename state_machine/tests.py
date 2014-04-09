from state_machine.models import ObjectState, SafetyLevel, VersionedM2M, ObjectExtender
from state_machine.queryset import VersionedForeignKey

import time
import datetime

from django.db import models
from django.db import connection
from django.test import TestCase
from django.core.management.color import no_style
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User

#===============================================================================
""" Fake but *instantiatable* classes are defined here to test abstract classes
for state_machine models. """

class FakeModel( ObjectState ):
    """ simple versioned model """
    test_attr = models.IntegerField()

class FakeParentModel( ObjectState ):
    """ versioned model with M2M relationship and reverse FK relationship """
    test_attr = models.IntegerField()
    m2m = models.ManyToManyField(FakeModel, through='parent_fake', blank=True, null=True)

class FakeChildModel( ObjectState ):
    """ simple versioned model with parent """
    test_attr = models.IntegerField()
    test_ref = VersionedForeignKey( FakeParentModel )

class parent_fake( VersionedM2M ):
    """ M2M relationship class """
    parent = VersionedForeignKey( FakeParentModel )
    fake = VersionedForeignKey( FakeModel )

#===============================================================================
""" these methods create / delete tables for fake models. Actually unittest does
the creation itself, so create_fake_model() and  delete_fake_model() methods are
not used."""

def create_fake_model( prototype ):
    """ Create the schema for our prototype model """
    sql, _ = connection.creation.sql_create_model(prototype, no_style())
    _cursor = connection.cursor()
    for statement in sql:
        _cursor.execute(statement)
    # versioned objects require PRIMARY KEY change
    if issubclass(prototype, ObjectState):
        update_keys_for_model( prototype )

def update_keys_for_model( model ):
    """ Versioned models need to have changes in the DB schema, in particular
    the PK should be changed from 'local_id' to the 'guid' """
    sql = []
    db_table = model._meta.db_table
    sql.append(''.join(["ALTER TABLE `", db_table, "` DROP PRIMARY KEY;"]))
    sql.append(''.join(["ALTER TABLE `", db_table, "` ADD PRIMARY KEY (`guid`);"]))
    _cursor = connection.cursor()
    for statement in sql:
        _cursor.execute(statement)

def delete_fake_model( model ):
    """ Delete the schema for the test model """
    sql = connection.creation.sql_destroy_model(model, (), no_style())
    _cursor = connection.cursor()
    for statement in sql:
        _cursor.execute(statement)

#===============================================================================
""" Tests """

class TestVersionedQuerySet(TestCase):
    """
    Base test class for versioned QuerySet testing.
    """
    model = None
    fixtures = ["users.json"]

    def setUp(self):
        update_keys_for_model( FakeModel ) # could be done only once..
        self.model = FakeModel

    def test_create(self):
        obj = self.model.objects.create( test_attr = 1, owner = User.objects.get( pk = 1 ) )
        self.assertGreater( self.model.objects.count(), 0 )

    def test_update(self):
        # 1. create test object
        obj = self.model.objects.create( test_attr = 1, owner = User.objects.get( pk = 1 ) )
        time.sleep(1)

        # 2. update test attribute
        self.model.objects.filter( pk = obj.pk ).update( test_attr = 2 )

        # 3. make sure it has been changed
        upd_obj = self.model.objects.get( pk = obj.pk)
        self.assertEqual( getattr(upd_obj, 'test_attr'), 2 )

        # 4. make sure older version is correct and accessible
        old_obj = self.model.objects.filter(at_time = obj.date_created).get( pk = obj.pk )
        self.assertEqual( getattr(old_obj, 'test_attr'), 1 )

    def test_delete(self):
        # 1. create test object
        obj = self.model.objects.create( test_attr = 1, owner = User.objects.get( pk = 1 ) )
        time.sleep(1)

        # 2. delete object
        self.model.objects.filter( pk = obj.pk ).delete()

        # 3. make sure it was deleted
        try:
            self.model.objects.get( pk = obj.pk )
        except ObjectDoesNotExist:
            pass
        else:
            raise AssertionError("object was not deleted properly")

        # 4. make sure older version is correct and accessible
        old_obj = self.model.objects.filter(at_time = obj.date_created).get( pk = obj.pk )
        self.assertEqual( getattr(old_obj, 'test_attr'), 1 )

    def test_bulk_create(self):
        objects = []
        for attr in [15, 16, 17]:
            objects.append( self.model( test_attr = attr, owner = User.objects.get(pk = 1) ) )
        self.model.objects.bulk_create( objects )
        self.assertGreater( self.model.objects.count(), 0 )

    def test_exists(self):
        obj = self.model.objects.create( test_attr = 1, owner = User.objects.get( pk = 1 ) )
        self.assertTrue( self.model.objects.exists() )

    def test_all(self):
        obj = self.model.objects.create( test_attr = 1, owner = User.objects.get( pk = 1 ) )
        obj = self.model.objects.create( test_attr = 2, owner = User.objects.get( pk = 1 ) )
        self.assertEqual( len( self.model.objects.all() ), 2 )

    def test_count(self):
        obj = self.model.objects.create( test_attr = 1, owner = User.objects.get( pk = 1 ) )
        obj = self.model.objects.create( test_attr = 2, owner = User.objects.get( pk = 1 ) )
        self.assertEqual( self.model.objects.count(), 2 )

    def test_filter(self):
        obj = self.model.objects.create( test_attr = 1, owner = User.objects.get( pk = 1 ) )
        obj = self.model.objects.create( test_attr = 2, owner = User.objects.get( pk = 1 ) )
        self.assertEqual( self.model.objects.filter( test_attr = 1 ).count(), 1 )

    def tearDown(self):
        self.model.objects.all().delete()


class TestObjectState(TestCase):
    """
    Base test class for VersionedObjectManager testing. The fill_relations
    method should retrieve and pre-cache objects with all relatives.
    """
    fixtures = ["users.json"]

    def setUp(self):
        for model in [FakeModel, FakeParentModel, FakeChildModel]:
            update_keys_for_model( model ) # could be done only once..

    def test_basic(self):
        """ basic test to make sure versioned relationships working """
        owner = User.objects.get( pk = 1 )

        # 1. create 3 parent objects: P1, P2, P3
        parents = []
        for attr in [1, 2, 3]:
            par = FakeParentModel.objects.create( test_attr = attr, owner = owner )
            parents.append( par )
        for par in parents: # test no children
            self.assertEqual( par.fakechildmodel_set.count(), 0 )

        # 2. create two children for P1
        children = []
        P1 = FakeParentModel.objects.get( pk=1 )
        for attr in [1, 2]:
            chld = FakeChildModel.objects.create( test_attr = attr, owner = \
                owner, test_ref = P1 )
            children.append( chld )
        self.assertEqual( getattr( P1, 'fakechildmodel_set').all().count(), 2 )

        # 3. create two M2M objects, referencing P1 and P2 respectively
        m2ms = []
        P2 = FakeParentModel.objects.get( pk=2 )
        for attr in [1, 2]:
            m2m = FakeModel.objects.create( test_attr = attr, owner = owner )
            m2ms.append( m2m )
        m2m1 = FakeModel.objects.get( pk=1 )
        m2m_ids = [x.pk for x in m2ms]
        FakeParentModel.save_changes( [P1], {}, {"m2m": m2m_ids}, {}, True )
        FakeParentModel.save_changes( [P2], {}, {"m2m": m2m_ids}, {}, True )
        self.assertEqual( getattr( P1, 'm2m').all().count(), 2 )
        self.assertEqual( getattr( m2m1, 'fakeparentmodel_set').all().count(), 2 )
        bp = datetime.datetime.now()
        time.sleep( 1 )

        # 4. delete P2
        P2.delete()
        self.assertEqual( getattr( m2m1, 'fakeparentmodel_set').all().count(), 1 )

        # 5. delete m2m1
        m2m1.delete()
        m2m2 = FakeModel.objects.get( pk=2 )
        self.assertEqual( getattr( P1, 'm2m').all().count(), 1 )
        self.assertEqual( getattr( P1, 'm2m').all()[0].pk, m2m2.pk )

        # 5. delete first child
        FakeChildModel.objects.get( pk=1 ).delete()
        self.assertEqual( getattr( P1, 'fakechildmodel_set').all().count(), 1 )

        # 6. test an old object has all relations
        P1_old = FakeParentModel.objects.filter(at_time = bp).get( pk=1 )
        self.assertEqual( getattr( P1_old, 'm2m').all().count(), 2 )
        self.assertEqual( getattr( P1_old, 'fakechildmodel_set').all().count(), 2 )

    def test_fetch_related(self):
        """ testing how the fill_relations() function works (fast fetching 
        objects with relationships) """
        owner = User.objects.get( pk = 1 )

        # 1. create 2 parent objects: P1, P2
        P1 = FakeParentModel.objects.create( test_attr = 1, owner = owner )
        P2 = FakeParentModel.objects.create( test_attr = 2, owner = owner )

        # 2. create 2 children for P1 and 1 for P2
        C1 = FakeChildModel.objects.create( test_attr=1, owner=owner, test_ref=P1 )
        C2 = FakeChildModel.objects.create( test_attr=2, owner=owner, test_ref=P1 )
        C3 = FakeChildModel.objects.create( test_attr=3, owner=owner, test_ref=P2 )

        # 3. create two M2M objects, referencing P1 and P2 respectively
        m2m1 = FakeModel.objects.create( test_attr = 1, owner = owner )
        m2m2 = FakeModel.objects.create( test_attr = 2, owner = owner )
        m2m_ids = [x.pk for x in [m2m1, m2m2]]
        FakeParentModel.save_changes( [P1], {}, {"m2m": m2m_ids}, {}, True )
        FakeParentModel.save_changes( [P2], {}, {"m2m": m2m_ids}, {}, True )

        bp = datetime.datetime.now()
        time.sleep( 1 )

        # assert object has 2 direct children and 2 M2M children
        P1 = FakeParentModel.objects.filter( pk=1 )
        P1 = ObjectExtender( P1.model ).fill_relations( P1 )[0]
        self.assertEqual( len(getattr(P1, 'fakechildmodel_set_buffer_ids')), 2)
        self.assertEqual( len(getattr(P1, 'm2m_buffer_ids')), 2)

        # delete some relatives
        C2.delete()
        m2m2.delete()

        # assert object has now only 1 direct child and 1 M2M child
        P1 = FakeParentModel.objects.filter( pk=1 )
        P1 = ObjectExtender( P1.model ).fill_relations( P1 )[0]
        self.assertEqual( len(getattr(P1, 'fakechildmodel_set_buffer_ids')), 1)
        self.assertEqual( len(getattr(P1, 'm2m_buffer_ids')), 1)

        # assert previous relations accessible back in time
        P1 = FakeParentModel.objects.filter( at_time=bp, pk=1 )
        P1 = ObjectExtender( P1.model ).fill_relations( P1, _at_time=bp )[0]
        self.assertEqual( len(getattr(P1, 'fakechildmodel_set_buffer_ids')), 2)
        self.assertEqual( len(getattr(P1, 'm2m_buffer_ids')), 2)


    def tearDown(self):
        for model in [FakeModel, FakeParentModel, FakeChildModel, parent_fake]:
            model.objects.all().delete()


