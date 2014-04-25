import simplejson as json
import string
import random
from datetime import datetime
from django.contrib.auth.models import User
from django.utils import timezone
from tastypie.test import ResourceTestCase
from rest.resource import BaseFileResourceMixin


class TestApi(ResourceTestCase):
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

    def get_available_objs(self, resource, user):
        model = resource.Meta.queryset.model
        if hasattr(model, 'security_filter'):
            return model.security_filter(model.objects.all(), user)
        else:
            return model.objects.filter(owner=user)

    def build_dummy_json(self, resource, user):
        fields = resource.build_schema()['fields']

        dummy = {}
        file_fields = getattr(resource, "file_fields", {})
        for name, meta in [(k, v) for k, v in fields.items() if not v['readonly']]:

            if name in file_fields.keys() or name == 'safety_level' or \
                    name.endswith('__unit') or name == 'document':
                continue  # these fields have good default values

            if meta['type'] == 'related':
                if meta['related_type'] == 'to_one':  # ignore to_many for now
                    dummy[name] = random.choice(
                        self.get_available_objs(
                            getattr(resource, name).to_class, user
                        )
                    ).pk

                elif meta['related_type'] == 'to_many' and \
                                name == 'recordingchannelgroup':
                    dummy[name] = [random.choice(
                        self.get_available_objs(
                            getattr(resource, name).to_class, user
                        )
                    ).pk]  # set one random RCG
            else:
                dummy[name] = self.RANDOM_GENERATORS[meta['type']]()

        return dummy

    def validate_json_response(self, dummy, json_obj):
        for k, v in dummy.items():
            new = json_obj[k]
            if isinstance(new, list):
                continue  # skips m2m FIXME

            if not isinstance(new, basestring):
                self.assertEqual(json_obj[k], v)
                continue

            try:
                new = datetime.strptime(json_obj[k], "%Y-%m-%dT%H:%M:%S")
                self.assertEqual(new.strftime("%Y-%m-%d %H:%M:%S"), v)

            except ValueError:  # not a datetime field
                if new.lower().startswith('http'):
                    self.assertTrue(v in new, ", ".join([v, new]))
                else:
                    self.assertEqual(json_obj[k], v)

    def test_list(self):
        def validate_obj_count(count):
            self.login(user)

            response = self.client.get(url)
            data = json.loads(response.content)
            self.assertEqual(response.status_code, 200, response.content)
            self.assertEqual(len(data[resource.Meta.collection_name]), count)

            self.logout()

        for resource in self.resources:
            name = resource.Meta.resource_name
            ver = resource.Meta.api_name
            url = "/api/%s/%s/?format=json" % (ver, name)

            for user in [self.bob, self.ed]:
                count = self.get_available_objs(resource, user).count()
                validate_obj_count(count)

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

            res_name = resource.Meta.resource_name
            ver = resource.Meta.api_name
            obj = self.get_available_objs(resource, self.bob)[0]

            for name, field in resource.file_fields.items():
                url = "/api/%s/%s/%s/%s/" % (ver, res_name, obj.local_id, name)

                self.login(self.ed)

                response = self.client.get(url)
                self.assertEqual(response.status_code, 401, response.content)

                self.logout()
                self.login(self.bob)

                response = self.client.get(url)
                try:
                    filepath = getattr(obj, name).path
                    self.assertEqual(response.status_code, 200)
                except ValueError:
                    self.assertEqual(response.status_code, 204)

    def test_create(self):
        self.login(self.bob)

        for resource in self.resources:
            name = resource.Meta.resource_name
            ver = resource.Meta.api_name
            url = "/api/%s/%s/" % (ver, name)

            dummy = self.build_dummy_json(resource, self.bob)
            kwargs = {'content_type': "application/json"}
            response = self.client.post(url, json.dumps(dummy), **kwargs)

            self.assertEqual(response.status_code, 201, response.content)

            # TODO update data-fields

    def test_update(self):
        for resource in self.resources:
            name = resource.Meta.resource_name
            ver = resource.Meta.api_name
            obj = self.get_available_objs(resource, self.bob)[0]
            url = "/api/%s/%s/%s/" % (ver, name, obj.local_id)

            dummy = self.build_dummy_json(resource, self.bob)
            kwargs = {'content_type': "application/json"}

            self.login(self.bob)

            response = self.client.put(url, json.dumps(dummy), **kwargs)
            self.assertEqual(response.status_code, 200, response.content)
            json_obj = resource._meta.serializer.deserialize(
                response.content, format=response['Content-Type']
            )
            self.validate_json_response(dummy, json_obj)

            self.logout()
            self.login(self.ed)

            response = self.client.put(url, json.dumps(dummy), **kwargs)
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