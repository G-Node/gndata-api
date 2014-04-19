from django.contrib.auth.models import User
from tastypie.test import ResourceTestCase
from permissions.tests.assets import Assets
from permissions.tests.fake import FakeResource, FakeOwnedResource

class TestApi(ResourceTestCase):
    """
    Test class for per-object permissions testing.
    """

    fixtures = ["users.json"]

    def setUp(self):
        self.bob = User.objects.get(pk=1)
        self.ed = User.objects.get(pk=2)
        self.neo = User.objects.get(pk=3)
        self.api_version = 'v1'
        self.assets = Assets().fill()
        self.f_res = FakeResource()
        self.fo_res = FakeOwnedResource()

    def test_get_acl(self):
        obj = self.assets['owned'][1]  # object is shared via ACL
        name = self.fo_res.Meta.resource_name
        url = "/api/v1/%s/%d/acl/?format=json" % (name, obj.local_id)

        self.login(self.ed)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 401, response.content)

        # TODO login using tastypie

        self.logout()
        self.login(self.bob)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertValidJSONResponse(response)

        # TODO validate only one access for Ed in the response

    def test_update_acl(self):

        # FIXME DRY

        data = [{
            'user': '/api/v1/user/{0}/'.format(self.neo.pk),
            'level': '1'
        }]
        obj = self.assets['owned'][1]  # object is shared via ACL
        name = self.fo_res.Meta.resource_name
        url = "/api/v1/%s/%d/acl/?format=json" % (name, obj.local_id)

        self.login(self.ed)

        response = self.client.put(url, data)
        self.assertEqual(response.status_code, 401, response.content)

        self.logout()
        self.login(self.bob)

        response = self.client.put(url, data)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertValidJSONResponse(response)

        # TODO validate only one access for Neo in the response

    def test_access_public(self):
        pass

    def test_access_via_acl(self):
        pass

    def tearDown(self):
        self.assets.flush()
