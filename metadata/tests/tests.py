import simplejson as json

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from metadata.api import *
from rest.tests.assets import Assets


class TestApi(TestCase):
    """
    Base test class for BaseService testing.
    """
    fixtures = ["users.json"]

    def setUp(self):
        self.origin = timezone.now()
        self.assets = Assets().fill()
        self.bob = User.objects.get(pk=1)
        self.ed = User.objects.get(pk=2)
        self.api_version = 'v1'
        self.resources = [DocumentResource, SectionResource, PropertyResource,
                          ValueResource]

    def test_list(self):
        def get_available_objs(resource, user):
            model = resource.meta.queryset.model
            if hasattr(model, 'security_filter'):
                return model.security_filter(model.objects.all(), user)
            else:
                return model.objects.filter(owner=user)

        def validate_obj_count(url, user, count):
            self.login(user)

            response = self.client.get(url)
            data = json.loads(response.content)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(data['objects']), count)

            self.logout()

        for resource in self.resources:
            name = resource.meta.resource_name
            url = "/".join(["api", self.api_version, name]) + "?format=json"

            for user in [self.bob, self.ed]:
                count = get_available_objs(resource, user).count()
                validate_obj_count(url, user, count)

    def test_get(self):
        # also test back in time
        pass

    def test_create(self):
        pass

    def test_update(self):
        pass

    def test_delete(self):
        pass

    def login(self, user):
        logged = self.client.login(username=user.username, password="pass")
        self.assertTrue(logged)

    def logout(self):
        self.client.logout()

    def tearDown(self):
        Assets().flush()

