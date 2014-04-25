from gndata_api.utils import update_keys_for_model
from gndata_api.urls import metadata_resources
from rest.tests.base import TestApi
from metadata.tests.assets import Assets


class TestMetadataApi(TestApi):
    """
    Metadata resource API test class.
    """
    def setUp(self):
        super(TestMetadataApi, self).setUp()
        self.resources = metadata_resources
        for resource in self.resources:
            update_keys_for_model(resource.Meta.object_class)
        self.assets = Assets().fill()