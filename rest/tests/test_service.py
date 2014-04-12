from django.test import TestCase
from django.contrib.auth.models import User

from gndata_api.fake import *
from gndata_api.assets import Assets


class TestService(TestCase):
    """
    Base test class for BaseService testing.
    """
    fixtures = ["users.json"]

    def setUp(self):
        Assets.fill()
        self.owner = User.objects.get(pk=1)

    def test_list(self):
        pass

    def test_max_results(self):
        pass

    def test_offset(self):
        pass

    def test_filters(self):
        pass

    def test_excludes(self):
        pass

    def test_get(self):
        # authorized and non-authorized
        pass

    def test_create(self):
        pass

    def test_update(self):
        # authorized and non-authorized
        pass

    def test_delete(self):
        # authorized and non-authorized
        pass

    def tearDown(self):
        Assets.flush()

