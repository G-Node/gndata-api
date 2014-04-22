from django.contrib.auth.models import User
from django.core.files import File
from gndata_api.baseassets import BaseAssets
from ephys.models import *
from gndata_api.settings import FILE_MEDIA_ROOT

import os
import random
import h5py
import uuid


class Assets(BaseAssets):
    """
    Creates test Neo objects.
    """

    def __init__(self):
        self.models = [Block, Segment, EventArray, Event, EpochArray, Epoch,
                       RecordingChannelGroup, RecordingChannel, Unit,
                       SpikeTrain, AnalogSignalArray, AnalogSignal,
                       IrregularlySampledSignal, Spike]

    def make_dummy_file(self, obj_with_owner):
        uid = uuid.uuid1().hex
        filename = uid + '.h5'
        rel_path = make_upload_path(obj_with_owner, filename)
        fullpath = os.path.join(FILE_MEDIA_ROOT, rel_path)

        if not os.path.exists(fullpath.replace(filename, '')):
            os.makedirs(fullpath.replace(filename, ''))

        f = h5py.File(fullpath)
        f.create_dataset(name=uid, data=[2.48, 1.58, 9.30, 4.88, 4.75])
        f.close()

        return rel_path

    def fill(self):
        # collector for created objects
        assets = {
            "block": [],
            "segment": [],
            "eventarray": [],
            "event": [],
            "epocharray": [],
            "epoch": [],
            "rcg": [],
            "rc": [],
            "unit": [],
            "spiketrain": [],
            "analogsignalarray": [],
            "analogsignal": [],
            "irsa": [],
            "spike": []
        }

        bob = User.objects.get(pk=1)
        ed = User.objects.get(pk=2)

        # blocks
        for i in range(2):
            params = {
                'name': "Local Field Potential and Spike Data %d" % (i + 1),
                'owner': bob
            }
            obj = Block.objects.create(**params)
            assets["block"].append(obj)

        # RCGs
        for i in range(2):
            params = {
                'name': "Electrode group %d" % (i + 1),
                'block': assets['block'][0],
                'owner': bob
            }
            obj = RecordingChannelGroup.objects.create(**params)
            assets["rcg"].append(obj)

        # recording channels
        for i in range(4):
            params = {
                'name': "Electrode %d" % (i + 1),
                'index': (i + 1),
                'block': assets['block'][0],
                'owner': bob
            }
            obj = RecordingChannel.objects.create(**params)
            assets["rc"].append(obj)

        # units
        for i in range(3):
            params = {
                'name': "SUA-LFP-unit %d" % (i + 1),
                'block': assets['block'][0],
                'recordingchannelgroup': assets['rcg'][0],
                'owner': bob
            }
            obj = Unit.objects.create(**params)
            assets["unit"].append(obj)

        # segments
        for i in range(10):
            params = {
                'name': "Segment %d" % (i + 1),
                'block': assets['block'][0],
                'owner': bob
            }
            obj = Segment.objects.create(**params)
            assets["segment"].append(obj)

        # event arrays
        for i in range(4):
            parent = assets['segment'][0] if i < 2 else assets['segment'][1]
            params = {
                'name': "SUA-LFP-unit %d" % (i + 1),
                'labels': self.make_dummy_file(parent),
                'times': self.make_dummy_file(parent),
                'times__unit': 'ms',
                'segment': parent,
                'owner': bob
            }
            obj = EventArray.objects.create(**params)
            assets["eventarray"].append(obj)