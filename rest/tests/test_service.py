import time

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from rest.service import BaseService
from gndata_api.fake import *
from rest.tests.assets import Assets


class TestService(TestCase):
    """
    Base test class for BaseService testing.
    """
    fixtures = ["users.json"]

    def setUp(self):
        self.assets = Assets.fill()
        self.bob = User.objects.get(pk=1)
        self.ed = User.objects.get(pk=2)
        self.srv = BaseService(FakeModel)
        self.origin = timezone.now()

    def test_list(self):
        self.assertEqual(len(self.srv.list(self.bob)), 3)
        self.assertEqual(len(self.srv.list(self.ed)), 1)

    def test_max_results(self):
        self.assertEqual(len(self.srv.list(self.bob, max_results=2)), 2)

    def test_offset(self):
        self.assertEqual(len(self.srv.list(self.bob, offset=2)), 1)

    def test_filters(self):
        filters = [('test_attr__gt', '2')]
        selected = self.srv.list(self.bob, filters=filters)
        self.assertEqual(len(selected), 1)
        self.assertTrue(selected[0].test_attr > 2)

        filters = [('test_str_attr__icontains', 'three')]
        selected = self.srv.list(self.bob, filters=filters)
        self.assertEqual(len(selected), 1)
        self.assertTrue(selected[0].test_str_attr == 'three')

        # test public object with alien owner

    def test_excludes(self):
        pass

    def test_get(self):
        fm = self.assets["fake"][0]

        self.assertRaises(self.srv.get(self.ed, 12345678), ObjectDoesNotExist)

        # authorized
        selected = self.srv.get(self.bob, fm.pk)
        self.assertEqual(selected.test_attr, fm.test_attr)

        # non-authorized
        self.assertRaises(self.srv.get(self.ed, fm.pk), ReferenceError)

        time.sleep(1)

        fm.test_attr = 271828
        fm.save()

        # unchanged
        selected = self.srv.get(self.bob, fm.pk, at_time=self.origin)
        self.assertEqual(selected.test_attr, 1)

    def test_create(self):
        count = FakeModel.objects.all().count()

        fm = self.assets["fake"][0]
        obj = self.srv.create(self.ed, fm)

        fresh = FakeModel.objects.all().get(pk=obj.pk)
        self.assertEqual(fresh.test_attr, obj.test_attr)
        self.assertEqual(FakeModel.objects.all().count(), count + 1)

    def test_update(self):
        fm = self.assets["fake"][0]
        fm.test_attr = 271828

        # authorized
        obj = self.srv.update(self.bob, fm.pk, fm)

        fresh = FakeModel.objects.all().get(pk=obj.pk)
        self.assertEqual(fresh.test_attr, obj.test_attr)

        # non-authorized
        self.assertRaises(self.srv.update(self.bob, fm.pk, fm), ReferenceError)

    def test_delete(self):
        count = FakeModel.objects.all().count()
        fm = self.assets["fake"][0]

        # non-authorized
        self.assertRaises(self.srv.delete(self.bob, fm.pk), ReferenceError)

        # authorized
        self.srv.delete(self.bob, fm.pk)

        self.assertRaises(FakeModel.objects.all().get(pk=fm.pk), ObjectDoesNotExist)
        self.assertEqual(FakeModel.objects.all().count(), count - 1)

    def tearDown(self):
        Assets.flush()

