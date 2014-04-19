from django.contrib.auth.models import User
from tastypie.test import ResourceTestCase
from permissions.tests.assets import Assets


class TestApi(ResourceTestCase):
    """
    Test class for per-object permissions testing.
    """

    fixtures = ["users.json"]

    def setUp(self):
        self.bob = User.objects.get(pk=1)
        self.ed = User.objects.get(pk=2)
        self.api_version = 'v1'
        self.assets = Assets().fill()

    def test_get_acl(self):
        pass

    def test_update_acl(self):
        pass

    def test_access_public(self):
        pass

    def test_access_via_acl(self):
        pass

    def tearDown(self):
        self.assets.flush()
