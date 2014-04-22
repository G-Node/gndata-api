from django.contrib.auth.models import User
from tastypie.test import ResourceTestCase
from permissions.tests.assets import Assets
from permissions.tests.fake import FakeResource, FakeOwnedResource
from permissions.models import SingleAccess

import simplejson as json


class TestApi(ResourceTestCase):
    """
    Test class for per-object permissions testing.
    """

    fixtures = ["users.json"]

    def setUp(self):
        super(TestApi, self).setUp()
        self.bob = User.objects.get(pk=1)
        self.ed = User.objects.get(pk=2)
        self.neo = User.objects.get(pk=3)
        self.api_version = 'v1'
        self.assets = Assets().fill()
        self.f_res = FakeResource()
        self.fo_res = FakeOwnedResource()

    def get_auth(self, user):
        # TODO check why this does not work
        return self.create_basic(username=user.username, password="pass")

    def login(self, user):
        logged = self.client.login(username=user.username, password="pass")
        self.assertTrue(logged)

    def logout(self):
        self.client.logout()

    def test_get_acl(self):
        obj = self.assets['owned'][1]  # object is shared via ACL
        name = self.fo_res.Meta.resource_name
        url = "/api/v1/%s/%d/acl/?format=json" % (name, obj.local_id)

        # this does not proxy user credentials correctly, TODO find out why
        #auth = self.get_auth(self.ed)
        #response = self.api_client.get(url, format='json', authentication=auth)

        self.login(self.ed)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401, response.content)

        self.logout()
        self.login(self.bob)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertValidJSONResponse(response)

        data = self.deserialize(response)

        ed_url = '/api/v1/user/{0}/'.format(self.ed.username)
        self.assertEqual(data[0]['user'], ed_url)
        self.assertEqual(data[0]['access_level'], 1)

    def test_update_acl(self):
        data = json.dumps([{
            "user": "/api/v1/user/{0}/".format(self.neo.username),
            "access_level": 1
        }])
        obj = self.assets['owned'][1]  # object is shared via ACL
        name = self.fo_res.Meta.resource_name
        url = "/api/v1/%s/%d/acl/?format=json" % (name, obj.local_id)

        self.login(self.ed)
        response = self.client.put(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 401, response.content)

        self.login(self.bob)
        response = self.client.put(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertValidJSONResponse(response)

        data = self.deserialize(response)

        neo_url = '/api/v1/user/{0}/'.format(self.neo.username)
        self.assertEqual(data[0]['user'], neo_url)
        self.assertEqual(data[0]['access_level'], 1)

        self.assertEqual(SingleAccess.objects.count(), 1)  # not changed
        new_username = SingleAccess.objects.all()[0].access_for.username
        self.assertEqual(new_username, self.neo.username)

    def test_access_public(self):
        pass

    def test_access_via_acl(self):
        pass