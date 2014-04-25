from gndata_api.utils import update_keys_for_model
from gndata_api.urls import ephys_resources
from rest.tests.base import TestApi
from ephys.tests.assets import Assets


class TestEphysApi(TestApi):
    """
    Ephys resource API test class.
    """
    def setUp(self):
        super(TestEphysApi, self).setUp()
        self.resources = ephys_resources
        for resource in self.resources:
            update_keys_for_model(resource.Meta.object_class)
        self.assets = Assets().fill()