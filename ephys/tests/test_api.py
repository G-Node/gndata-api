from gndata_api.utils import update_keys_for_model
from gndata_api.urls import EPHYS_RESOURCES
from rest.tests.base import TestApi
from ephys.tests.assets import Assets


class TestEphysApi(TestApi):
    """
    Ephys resource API test class.
    """
    def setUp(self):
        super(TestEphysApi, self).setUp()
        self.resources = [
            EPHYS_RESOURCES['eventarray'],
            EPHYS_RESOURCES['event'],
            EPHYS_RESOURCES['epocharray'],
            EPHYS_RESOURCES['epoch'],
            EPHYS_RESOURCES['spiketrain'],
            EPHYS_RESOURCES['analogsignalarray'],
            EPHYS_RESOURCES['analogsignal'],
            EPHYS_RESOURCES['irregularlysampledsignal'],
            EPHYS_RESOURCES['spike'],
            EPHYS_RESOURCES['segment'],
            EPHYS_RESOURCES['unit'],
            EPHYS_RESOURCES['recordingchannel'],
            EPHYS_RESOURCES['recordingchannelgroup'],
            EPHYS_RESOURCES['block']
        ]
        for resource in self.resources:
            update_keys_for_model(resource.Meta.object_class)
        self.assets = Assets().fill()