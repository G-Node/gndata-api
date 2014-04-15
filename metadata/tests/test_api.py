import simplejson as json

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder

from tastypie.serializers import Serializer

from metadata.api import *
from metadata.tests.assets import Assets
from gndata_api.fake import update_keys_for_model


class TestApi(TestCase):
    """
    Base test class for Resource API testing.
    """

    # TODO make this test user-invariant

    fixtures = ["users.json"]

    def setUp(self):
        self.origin = timezone.now()
        self.bob = User.objects.get(pk=1)
        self.ed = User.objects.get(pk=2)
        self.api_version = 'v1'
        self.resources = [
            ValueResource, PropertyResource, SectionResource, DocumentResource
        ]
        for resource in self.resources:
            update_keys_for_model(resource.Meta.object_class)
        self.assets = Assets().fill()

    def get_available_objs(self, resource, user):
        model = resource.Meta.queryset.model
        if hasattr(model, 'security_filter'):
            return model.security_filter(model.objects.all(), user)
        else:
            return model.objects.filter(owner=user)

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
            url = "/api/%s/%s/?format=json" % (self.api_version, name)

            for user in [self.bob, self.ed]:
                count = self.get_available_objs(resource, user).count()
                validate_obj_count(url, user, count)

    def test_get(self):
        # TODO also test back in time
        for resource in self.resources:
            obj = self.get_available_objs(resource, self.bob)[0]
            name = resource.Meta.resource_name
            url = "/api/%s/%s/%d/?format=json" % (self.api_version, name, obj.local_id)

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
            url = "/api/%s/%s/" % (self.api_version, name)

            obj = self.get_available_objs(resource, self.bob)[0]

            res = resource()
            bundle = res.build_bundle(obj=obj)
            res.full_dehydrate(bundle)  # some magic here
            res.full_dehydrate(bundle)  # no clue why this is needed twice..

            bundle.obj.local_id = None  # new object
            bundle.data.pop('local_id')

            post = Serializer().to_json(bundle)
            kwargs = {'content_type': "application/json"}
            response = self.client.post(url, post, **kwargs)

            self.assertEqual(response.status_code, 201, response.content)

    def test_update(self):
        for resource in self.resources:
            obj = self.get_available_objs(resource, self.bob)[0]

            name = resource.Meta.resource_name
            url = "/api/%s/%s/%d/" % (self.api_version, name, obj.local_id)

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
            url = "/api/%s/%s/%d/" % (self.api_version, name, obj.local_id)

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