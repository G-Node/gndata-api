import time

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from rest._service import BaseService
from rest.tests.fake import *
from rest.tests.assets import Assets


class TestService(TestCase):
    """
    Base test class for BaseService testing.
    """
    fixtures = ["users.json"]

    def setUp(self):
        self.assets = Assets().fill()
        self.bob = User.objects.get(pk=1)
        self.ed = User.objects.get(pk=2)
        self.srv1 = BaseService(RestFakeModel)
        self.srv2 = BaseService(RestFakeOwnedModel)
        self.origin = timezone.now()

    def test_list(self):
        self.assertEqual(len(self.srv1.list(self.bob)), 3)
        self.assertEqual(len(self.srv1.list(self.ed)), 1)

        self.assertEqual(len(self.srv2.list(self.ed)), 2)
        self.assertEqual(len(self.srv2.list(self.bob)), 4)

    def test_max_results(self):
        self.assertEqual(len(self.srv1.list(self.bob, max_results=2)), 2)

    def test_offset(self):
        self.assertEqual(len(self.srv1.list(self.bob, offset=2)), 1)

    def test_filters(self):
        filters = [('test_attr', '2')]
        selected = self.srv1.list(self.bob, filters=filters)
        self.assertEqual(len(selected), 1)
        self.assertTrue(selected[0].test_attr == 2)

        filters = [('test_str_attr__icontains', 'three')]
        selected = self.srv1.list(self.bob, filters=filters)
        self.assertEqual(len(selected), 1)
        self.assertTrue(selected[0].test_str_attr == 'three')

        # test public objects with foreign owner
        filters = [('owner__last_name__icontains', 'bolson')]
        selected = self.srv2.list(self.ed, filters=filters)
        self.assertEqual(len(selected), 2)

        filters = [('test_attr__gt', '2'), ('test_str_attr__startswith', 't')]
        selected = self.srv1.list(self.bob, filters=filters)
        self.assertEqual(len(selected), 1)

    def test_excludes(self):
        excludes = [('test_attr', '2')]
        selected = self.srv1.list(self.bob, excludes=excludes)
        self.assertEqual(len(selected), 2)

        excludes = [('test_str_attr__icontains', 'three')]
        selected = self.srv1.list(self.bob, excludes=excludes)
        self.assertEqual(len(selected), 2)

        # test public objects with foreign owner
        excludes = [('owner__last_name__icontains', 'bolson')]
        selected = self.srv2.list(self.ed, excludes=excludes)
        self.assertEqual(len(selected), 0)

        excludes = [('test_attr__gt', '2'), ('test_str_attr__startswith', 't')]
        selected = self.srv1.list(self.bob, excludes=excludes)
        self.assertEqual(len(selected), 1)

    def test_get(self):
        fm = self.assets["fake"][0]

        self.assertRaises(ObjectDoesNotExist, self.srv1.get, self.ed, 12345678)

        # authorized
        selected = self.srv1.get(self.bob, fm.pk)
        self.assertEqual(selected.test_attr, fm.test_attr)

        # non-authorized
        self.assertRaises(ReferenceError, self.srv1.get, self.ed, fm.pk)

        time.sleep(1)

        fm.test_attr = 271828
        fm.save()

        # unchanged
        selected = self.srv1.get(self.bob, fm.pk, at_time=self.origin)
        self.assertEqual(selected.test_attr, 1)

    def test_create(self):
        count = RestFakeModel.objects.all().count()

        fm = self.assets["fake"][0]
        obj = self.srv1.create(self.ed, fm)

        fresh = RestFakeModel.objects.all().get(pk=obj.pk)
        self.assertEqual(fresh.test_attr, obj.test_attr)
        self.assertEqual(RestFakeModel.objects.all().count(), count + 1)

    def test_update(self):
        fm = self.assets["fake"][0]
        fm.test_attr = 271828

        # authorized
        obj = self.srv1.update(self.bob, fm.pk, fm)

        fresh = RestFakeModel.objects.all().get(pk=obj.pk)
        self.assertEqual(fresh.test_attr, obj.test_attr)

        # non-authorized
        self.assertRaises(ReferenceError, self.srv1.update, self.ed, fm.pk, fm)

    def test_delete(self):
        count = RestFakeModel.objects.all().count()
        fm = self.assets["fake"][0]

        # non-authorized
        self.assertRaises(ReferenceError, self.srv1.delete, self.ed, fm.pk)

        # authorized
        self.srv1.delete(self.bob, fm.pk)

        self.assertRaises(ObjectDoesNotExist, RestFakeModel.objects.all().get, pk=fm.pk)
        self.assertEqual(RestFakeModel.objects.all().count(), count - 1)

    def tearDown(self):
        Assets().flush()

