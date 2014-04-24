import simplejson as json
import string
import random

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import models

from tastypie.serializers import Serializer
from rest.resource import BaseFileResourceMixin


class TestApi(TestCase):
    """
    Abstract Base test class for Resource API testing.
    """

    # TODO make this test user-invariant

    fixtures = ["users.json"]

    RANDOM_GENERATORS = {
        'string': lambda: "".join(
            [random.choice(string.ascii_letters) for n in xrange(15)]
        ),
        'float': lambda: random.uniform(0.1, 99.8),
        'integer': lambda: random.randint(0, 99),
        'datetime': lambda: timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
        'boolean': lambda: random.choice([True, False])
    }

    def setUp(self):
        self.origin = timezone.now()
        self.bob = User.objects.get(pk=1)
        self.ed = User.objects.get(pk=2)
        self.resources = []
        self.assets = {}

    def get_file_fields(self, resource):
        """ parses related model and returns FileField instances, if any """
        all_fields = resource.Meta.object_class._meta.local_fields
        return [f for f in all_fields if isinstance(f, models.FileField)]

    def get_available_objs(self, resource, user):
        model = resource.Meta.queryset.model
        if hasattr(model, 'security_filter'):
            return model.security_filter(model.objects.all(), user)
        else:
            return model.objects.filter(owner=user)

    def build_dummy_json(self, resource, user):
        fields = resource.build_schema()['fields']

        dummy = {}
        file_fields = [f.name for f in self.get_file_fields(resource)]
        for name, meta in [k for k, v in fields.items() if not v['readonly']]:

            if name in file_fields:
                continue

            if meta['type'] == 'related':
                dummy[name] = random.choice(
                    self.get_available_objs(getattr(resource, name).to, user)
                ).pk

            else:
                dummy[name] = self.RANDOM_GENERATORS[meta['type']]()

        return dummy

    def test_list(self):
        def validate_obj_count(url, user, count):
            self.login(user)

            response = self.client.get(url)
            data = json.loads(response.content)
            self.assertEqual(response.status_code, 200, response.content)
            self.assertEqual(len(data['objects']), count)

            self.logout()

        for resource in self.resources:
            name = resource.Meta.resource_name
            ver = resource.Meta.api_name
            url = "/api/%s/%s/?format=json" % (ver, name)

            for user in [self.bob, self.ed]:
                count = self.get_available_objs(resource, user).count()
                validate_obj_count(url, user, count)

    def test_get(self):
        # TODO also test back in time
        for resource in self.resources:
            name = resource.Meta.resource_name
            ver = resource.Meta.api_name
            obj = self.get_available_objs(resource, self.bob)[0]
            url = "/api/%s/%s/%s/?format=json" % (ver, name, obj.local_id)

            self.login(self.ed)

            response = self.client.get(url)
            self.assertEqual(response.status_code, 401, response.content)

            self.logout()
            self.login(self.bob)

            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, response.content)

    def test_get_data(self):
        for resource in self.resources:
            if not isinstance(resource, BaseFileResourceMixin):
                continue

            name = resource.Meta.resource_name
            ver = resource.Meta.api_name
            obj = self.get_available_objs(resource, self.bob)[0]

            for field in self.get_file_fields(resource):
                url = "/api/%s/%s/%s/%s" % (ver, name, obj.local_id, field.name)

                self.login(self.ed)

                response = self.client.get(url)
                self.assertEqual(response.status_code, 401, response.content)

                self.logout()
                self.login(self.bob)

                response = self.client.get(url)
                self.assertEqual(response.status_code, 200, response.content)

    def test_create(self):
        # generic test for a resource. assumes a copy of a random existing
        # object in JSON can be saved as a new object.
        self.login(self.bob)

        for resource in self.resources:
            name = resource.Meta.resource_name
            ver = resource.Meta.api_name
            url = "/api/%s/%s/" % (ver, name)

            """
            obj = self.get_available_objs(resource, self.bob)[0]

            res = resource()
            bundle = res.build_bundle(obj=obj)
            res.full_dehydrate(bundle)  # some magic here
            res.full_dehydrate(bundle)  # no clue why this is needed twice..

            bundle.obj.local_id = None  # new object
            bundle.data.pop('local_id')

            post = Serializer().to_json(bundle)
            """

            dummy = self.build_dummy_json(resource, self.bob)
            kwargs = {'content_type': "application/json"}
            response = self.client.post(url, json.dumps(dummy), **kwargs)

            self.assertEqual(response.status_code, 201, response.content)

    def test_update(self):
        for resource in self.resources:
            obj = self.get_available_objs(resource, self.bob)[0]

            name = resource.Meta.resource_name
            ver = resource.Meta.api_name
            url = "/api/%s/%s/%s/" % (ver, name, obj.local_id)

            res = resource()
            bundle = res.build_bundle(obj=obj)
            res.full_dehydrate(bundle)  # some magic here
            res.full_dehydrate(bundle)  # no clue why this is needed twice..

            bundle.obj.local_id = None  # clean ids
            bundle.data.pop('local_id')

            post = Serializer().to_json(bundle)
            kwargs = {'content_type': "application/json"}

            self.login(self.bob)

            response = self.client.put(url, post, **kwargs)
            self.assertEqual(response.status_code, 204, response.content)

            self.logout()
            self.login(self.ed)

            response = self.client.put(url, post, **kwargs)
            self.assertEqual(response.status_code, 401, response.content)

    def test_delete(self):
        for resource in self.resources:
            obj = self.get_available_objs(resource, self.bob)[0]
            name = resource.Meta.resource_name
            ver = resource.Meta.api_name
            url = "/api/%s/%s/%s/" % (ver, name, obj.local_id)

            self.login(self.ed)

            response = self.client.get(url)
            self.assertEqual(response.status_code, 401, response.content)

            self.logout()
            self.login(self.bob)

            response = self.client.delete(url)
            self.assertEqual(response.status_code, 204, response.content)

    def login(self, user):
        logged = self.client.login(username=user.username, password="pass")
        self.assertTrue(logged)

    def logout(self):
        self.client.logout()