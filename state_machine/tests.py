import datetime

from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User

from state_machine.fake import *
from state_machine.assets import Assets


class TestVersionedQuerySet(TestCase):
    """
    Base test class for versioned QuerySet testing.
    """
    fixtures = ["users.json"]

    def setUp(self):
        fake_models = [FakeModel, FakeParentModel, FakeChildModel]
        for model in fake_models:
            update_keys_for_model(model)
        Assets.fill()
        self.qs = FakeModel.objects
        self.owner = User.objects.get(pk=1)

    def test_create(self):
        created = self.qs.create(test_attr=271828, owner=self.owner)
        fetched = self.qs.get(pk=created.pk)
        self.assertEqual(created.test_attr, fetched.test_attr)

    def test_update(self):
        obj = self.qs.all()[0]

        self.qs.filter(pk=obj.pk).update(test_attr=271828)

        new_obj = self.qs.get(pk=obj.pk)
        self.assertEqual(new_obj.test_attr, 271828)

        old_obj = self.qs.filter(at_time=obj.date_created).get(pk=obj.pk)
        self.assertEqual(old_obj.test_attr, obj.test_attr)

    def test_delete(self):
        obj = self.qs.all()[0]
        count = self.qs.count()

        self.qs.filter(pk=obj.pk).delete()
        self.assertRaises(ObjectDoesNotExist, self.qs.get(pk=obj.pk))

        old_obj = self.qs.filter(at_time=obj.date_created).get(pk=obj.pk)
        self.assertEqual(getattr(old_obj, 'test_attr'), 1)
        self.assertEqual(self.qs.count(), count - 1)

    def test_bulk_create(self):
        objects = []
        count = self.qs.count()

        for attr in [15, 16, 17]:
            objects.append(FakeModel(test_attr=attr, owner=self.owner))

        self.qs.bulk_create(objects)
        self.assertEqual(self.qs.count(), count + 3)

    def test_exists(self):
        self.qs.all().delete()
        self.assertFalse(self.qs.exists())

        obj = self.qs.create(test_attr=1, owner=self.owner)
        self.assertTrue(self.qs.exists())

    def test_all(self):
        count = self.qs.count()
        self.assertEqual(len(self.qs.all()), count)

        obj = self.qs.create(test_attr=271828, owner=self.owner)
        self.assertEqual(len(self.qs.all()), count + 1)

    def test_count(self):
        self.assertEqual(self.qs.count(), 3)

        obj = self.qs.create(test_attr=1, owner=self.owner)
        self.assertEqual(self.qs.count(), 4)

    def test_filter(self):
        self.assertEqual(self.qs.filter(test_attr=1).count(), 1)

        obj = self.qs.create(test_attr=271828, owner=self.owner)

        filtered = self.qs.filter(test_attr=271828)
        self.assertEqual(filtered.count(), 1)
        self.assertEqual(filtered.test_attr, 271828)

    def tearDown(self):
        Assets.flush()


class TestObjectRelations(TestCase):
    """
    Base test class for testing versioned relations implemented in
    VersionedObjectManager.
    """
    fixtures = ["users.json"]

    def assert_fm1_not_changed(self, fm1):
        self.assertTrue(fm1.fakeparentmodel_set.exists())
        self.assertEqual(fm1.fakeparentmodel_set.all()[0].test_attr, 1)

    def assert_fm3_not_changed(self, fm3):
        self.assertFalse(fm3.fakeparentmodel_set.exists())

    def assert_fp1_not_changed(self, fp1):
        self.assertEqual(fp1.m2m.all().count(), 2)
        self.assertEqual(fp1.fakechildmodel_set.all().count(), 2)

    def assert_fp2_not_changed(self, fp2):
        self.assertEqual(fp2.fakechildmodel_set.all().count(), 1)

    def assert_fc1_not_changed(self, fc1):
        self.assertEqual(fc1.test_ref.test_attr, 1)

    def assert_fc3_not_changed(self, fc3):
        self.assertEqual(fc3.test_ref.test_attr, 2)

    def setUp(self):
        fake_models = [FakeModel, FakeParentModel, FakeChildModel]
        for model in fake_models:
            update_keys_for_model(model)
        self.owner = User.objects.get(pk=1)
        self.origin = datetime.datetime.now()

    def test_fk_parent(self):
        self.assertEqual(Assets.fc(1).test_ref.test_attr, 1)
        self.assertEqual(Assets.fc(3).test_ref.test_attr, 2)

    def test_fk_child(self):
        self.assertEqual(Assets.fp(1).fakechildmodel_set.all().count(), 2)
        self.assertEqual(Assets.fp(2).fakechildmodel_set.all()[0].test_attr, 3)

    def test_m2m_parent(self):
        self.assertEqual(Assets.fp(1).m2m.all().count(), 2)
        self.assertEqual(Assets.fp(2).m2m.all()[0].test_attr, 2)

    def test_m2m_child(self):
        self.assertEqual(Assets.fm(1).fakeparentmodel_set.all()[0].test_attr, 1)
        self.assertEqual(Assets.fm(2).fakeparentmodel_set.all()[0].test_attr, 2)
        self.assertFalse(Assets.fm(3).fakeparentmodel_set.exists())

    def test_m2m_child_delete(self):
        FakeModel.objects.filter(test_attr=1).delete()
        self.assertEqual(Assets.fp(1).m2m.all().count(), 1)
        self.assertEqual(Assets.fp(1).m2m.all()[0].test_attr, 2)

        self.assert_fm1_not_changed(Assets.fm(1, self.origin))
        self.assert_fp1_not_changed(Assets.fp(1, self.origin))

    def test_m2m_child_remove(self):
        Assets.fm(1).fakeparentmodel_set.remove(Assets.fp(1))
        self.assertFalse(Assets.fm(1).fakeparentmodel_set.exists())
        self.assertEqual(Assets.fp(1).m2m.all().count(), 1)
        self.assertEqual(Assets.fp(1).m2m.all()[0].test_attr, 2)

        self.assert_fm1_not_changed(Assets.fm(1, self.origin))
        self.assert_fp1_not_changed(Assets.fp(1, self.origin))

    def test_m2m_child_add(self):
        self.assertFalse(Assets.fm(3).fakeparentmodel_set.exists())
        Assets.fm(3).fakeparentmodel_set.add(Assets.fp(2))
        self.assertTrue(Assets.fm(3).fakeparentmodel_set.exists())
        self.assertEqual(Assets.fm(3).fakeparentmodel_set.all()[0].test_attr, 2)
        self.assertEqual(Assets.fp(2).m2m.all().count(), 2)

        self.assert_fm3_not_changed(Assets.fm(3, self.origin))

    def test_all_parent_delete(self):
        FakeParentModel.objects.filter(test_attr=1).delete()
        self.assertFalse(Assets.fm(1).fakeparentmodel_set.exists())
        self.assertTrue(Assets.fc(1).test_ref is None)
        self.assertTrue(Assets.fc(2).test_ref is None)

        self.assert_fm1_not_changed(Assets.fm(1, self.origin))
        self.assert_fc1_not_changed(Assets.fc(1, self.origin))

    def test_all_parent_remove(self):
        Assets.fp(1).m2m.remove(Assets.fm(1))
        Assets.fp(1).fakechildmodel_set.remove(Assets.fc(1))
        self.assertEqual(Assets.fp(1).m2m.all()[0].test_attr, 2)
        self.assertEqual(Assets.fp(1).fakechildmodel_set.all()[0].test_attr, 2)
        self.assertTrue(Assets.fc(1).test_ref is None)
        self.assertFalse(Assets.fm(1).fakeparentmodel_set.exists())

        self.assert_fc1_not_changed(Assets.fc(1, self.origin))
        self.assert_fp1_not_changed(Assets.fp(1, self.origin))
        self.assert_fm1_not_changed(Assets.fm(1, self.origin))

    def test_all_parent_add(self):
        Assets.fp(1).m2m.add(Assets.fm(3))
        self.assertEqual(Assets.fp(1).m2m.all().count(), 3)
        self.assertFalse(Assets.fm(3).fakeparentmodel_set.exists())

        self.assert_fp1_not_changed(Assets.fp(1, self.origin))
        self.assert_fm3_not_changed(Assets.fm(3, self.origin))

    def test_fk_child_delete(self):
        FakeChildModel.objects.filter(test_attr=1).delete()
        self.assertTrue(Assets.fp(1).fakechildmodel_set.all().count(), 1)
        self.assertEqual(Assets.fp(1).fakechildmodel_set.all()[0].test_attr, 2)

        self.assert_fc1_not_changed(Assets.fc(1, self.origin))
        self.assert_fp1_not_changed(Assets.fp(1, self.origin))

    def test_fk_child_assign(self):
        fc1 = Assets.fc(1)
        fc1.test_ref = Assets.fp(2)
        fc1.save()

        self.assertEqual(Assets.fc(1).test_ref.test_attr, 2)
        self.assertTrue(Assets.fp(1).fakechildmodel_set.all().count(), 1)
        self.assertTrue(Assets.fp(2).fakechildmodel_set.all().count(), 2)

        self.assert_fp1_not_changed(Assets.fp(1, self.origin))
        self.assert_fc1_not_changed(Assets.fc(1, self.origin))
        self.assert_fp2_not_changed(Assets.fp(2, self.origin))

    def test_fk_child_remove(self):
        fc3 = Assets.fc(3)
        fc3.test_ref = None
        fc3.save()

        self.assertEqual(Assets.fc(1).test_ref.test_attr, 2)
        self.assertTrue(Assets.fc(3).test_ref is None)
        self.assertFalse(Assets.fp(2).fakechildmodel_set.exists())

        self.assert_fc3_not_changed(Assets.fc(3, self.origin))
        self.assert_fp2_not_changed(Assets.fp(2, self.origin))

    def tearDown(self):
        Assets.flush()


class TestObjectState(TestCase):
    """
    Base test class for VersionedObjectManager testing. The fill_relations
    method should retrieve and pre-cache objects with all relatives.
    """
    fixtures = ["users.json"]

    def setUp(self):
        fake_models = [FakeModel, FakeParentModel, FakeChildModel]
        for model in fake_models:
            update_keys_for_model(model)
        self.owner = User.objects.get(pk=1)
        self.origin = datetime.datetime.now()

    def test_save_create(self):
        fm = FakeModel(test_attr=271828)
        fm.save()
        self.assertTrue(FakeModel.objects.filter(test_attr=271828).exists())

        qs = FakeModel.objects.filter(at_time=self.origin)
        self.assertFalse(qs.filter(test_attr=271828).exists())

    def test_save_update(self):
        fm = Assets.fm(1)
        fm.test_attr = 271828
        fm.save()
        self.assertTrue(FakeModel.objects.filter(test_attr=271828).exists())
        self.assertEqual(FakeModel.objects.get(test_attr=271828).pk, fm.pk)

        qs = FakeModel.objects.filter(at_time=self.origin)
        self.assertFalse(qs.filter(pk=fm.pk).test_attr == 271828)

    def test_delete(self):
        fp1 = Assets.fp(1)
        fp1.delete()

        self.assertRaises(ObjectDoesNotExist, Assets.fp(1))

        old_fp1 = Assets.fp(1, self.origin)
        self.assertTrue(old_fp1.test_attr, 1)

        # relations are tested in *delete methods in TestObjectRelations

    def tearDown(self):
        Assets.flush()


