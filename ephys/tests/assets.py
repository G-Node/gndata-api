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
        f.create_dataset(name=uid, data=[1.48, 2.58, 3.30, 3.88, 4.75])
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
                'name': "Event array %d" % (i + 1),
                'labels': self.make_dummy_file(parent),
                'times': self.make_dummy_file(parent),
                'times__unit': 'ms',
                'segment': parent,
                'owner': bob
            }
            obj = EventArray.objects.create(**params)
            assets["eventarray"].append(obj)

        # events
        for i in range(4):
            parent = assets['segment'][0] if i < 2 else assets['segment'][1]
            params = {
                'name': "Event %d" % (i + 1),
                'label': "Event label %d" % (i + 1),
                'time': 1.56,
                'time__unit': 'ms',
                'segment': parent,
                'owner': bob
            }
            obj = Event.objects.create(**params)
            assets["event"].append(obj)

        # epoch arrays
        for i in range(4):
            parent = assets['segment'][0] if i < 2 else assets['segment'][1]
            params = {
                'name': "Epoch array %d" % (i + 1),
                'labels': self.make_dummy_file(parent),
                'times': self.make_dummy_file(parent),
                'times__unit': 'ms',
                'durations': self.make_dummy_file(parent),
                'durations__unit': 'ms',
                'segment': parent,
                'owner': bob
            }
            obj = EpochArray.objects.create(**params)
            assets["epocharray"].append(obj)

        # epochs
        for i in range(4):
            parent = assets['segment'][0] if i < 2 else assets['segment'][1]
            params = {
                'name': "Epoch %d" % (i + 1),
                'label': "Epoch label %d" % (i + 1),
                'time': 1.56,
                'time__unit': 'ms',
                'duration': 5.23,
                'duration__unit': 'ms',
                'segment': parent,
                'owner': bob
            }
            obj = Epoch.objects.create(**params)
            assets["epoch"].append(obj)

        # spike trains
        for i in range(4):
            segment = assets['segment'][0] if i < 2 else assets['segment'][1]
            unit = assets['unit'][0] if i < 2 else assets['unit'][1]
            params = {
                'name': "Spiketrain %d" % (i + 1),
                't_start': 0.56,
                't_start__unit': 'ms',
                't_stop': 5.23,
                't_stop__unit': 'ms',
                'times': self.make_dummy_file(segment),
                'times__unit': 'ms',
                'segment': segment,
                'unit': unit,
                'owner': bob
            }
            obj = SpikeTrain.objects.create(**params)
            assets["spiketrain"].append(obj)

        # analog signal arrays
        for i in range(4):
            segment = assets['segment'][0] if i < 2 else assets['segment'][1]
            rcg = assets['rcg'][0] if i < 3 else assets['rcg'][1]
            params = {
                'name': "ASA %d" % (i + 1),
                't_start': 1.56,
                't_start__unit': 'ms',
                'sampling_rate': 10000.0,
                'sampling_rate__unit': 'Hz',
                'signal': self.make_dummy_file(segment),
                'signal__unit': 'mV',
                'segment': segment,
                'recordingchannelgroup': rcg,
                'owner': bob
            }
            obj = AnalogSignalArray.objects.create(**params)
            assets["analogsignalarray"].append(obj)

        # analog signals
        for i in range(4):
            segment = assets['segment'][0] if i < 2 else assets['segment'][1]
            rc = assets['rc'][0] if i < 3 else assets['rc'][1]
            params = {
                'name': "Analog signal %d" % (i + 1),
                't_start': 1.56,
                't_start__unit': 'ms',
                'sampling_rate': 10000.0,
                'sampling_rate__unit': 'Hz',
                'signal': self.make_dummy_file(segment),
                'signal__unit': 'mV',
                'segment': segment,
                'recordingchannel': rc,
                'owner': bob
            }
            obj = AnalogSignal.objects.create(**params)
            assets["analogsignal"].append(obj)

        # irsa-s
        for i in range(4):
            segment = assets['segment'][0] if i < 2 else assets['segment'][1]
            rc = assets['rc'][0] if i < 3 else assets['rc'][1]
            params = {
                'name': "Irregular signal %d" % (i + 1),
                't_start': 1.56,
                't_start__unit': 'ms',
                'signal': self.make_dummy_file(segment),
                'signal__unit': 'mV',
                'times': self.make_dummy_file(segment),
                'times__unit': 'ms',
                'segment': segment,
                'recordingchannel': rc,
                'owner': bob
            }
            obj = IrregularlySampledSignal.objects.create(**params)
            assets["irsa"].append(obj)

        # spikes
        for i in range(4):
            segment = assets['segment'][0] if i < 2 else assets['segment'][1]
            unit = assets['unit'][0] if i < 2 else assets['unit'][1]
            params = {
                'name': "Spike waveform %d" % (i + 1),
                'time': 1.56,
                'time__unit': 'ms',
                'sampling_rate': 10000.0,
                'sampling_rate__unit': 'Hz',
                'left_sweep': 1.56,
                'left_sweep__unit': 'ms',
                'waveform': self.make_dummy_file(segment),
                'waveform__unit': 'mV',
                'segment': segment,
                'unit': unit,
                'owner': bob
            }
            obj = Spike.objects.create(**params)
            assets["spike"].append(obj)

        return assets