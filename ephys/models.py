from django.db import models
from django.core.files import storage
from state_machine.models import BaseGnodeObject
from state_machine.versioning.models import VersionedM2M
from state_machine.versioning.descriptors import VersionedForeignKey
from ephys.security import BlockBasedPermissionsMixin
from ephys.fields import TimeUnitField, SignalUnitField, SamplingUnitField
from permissions.models import BasePermissionsMixin
from gndata_api import settings

# TODO implement proper slicing

# TODO create data and metadata connection

# TODO make nicer upload paths?


def make_upload_path(self, filename):
    """ Generates upload path for FileField """
    return "%s/%s" % (self.owner.username, filename)

fs = storage.FileSystemStorage(location=settings.FILE_MEDIA_ROOT)

DEFAULTS = {
    "name_max_length": 100,
    "description_max_length": 2048,
    "label_max_length": 100,
    "unit_max_length": 10,
    "default_time_unit": "ms",
    "default_data_unit": "mV",
    "default_samp_unit": "Hz"
}


# 1 (of 15)
class Block(BasePermissionsMixin, BaseGnodeObject):
    """
    NEO Block @ G-Node.
    """
    # NEO attributes
    name = models.CharField(max_length=DEFAULTS['name_max_length'])
    description = models.CharField(max_length=1024, blank=True, null=True)
    filedatetime = models.DateTimeField(null=True, blank=True)
    index = models.IntegerField(null=True, blank=True)

    @property
    def size(self):
        return sum([s.size for s in self.segment_set.all()])

    def __unicode__(self):
        return self.name


class BaseInfo(BaseGnodeObject):
    """ Base abstract class for any NEO object (except Block) """

    # block reference is used to determine access to an object
    block = VersionedForeignKey(Block)
    description = models.CharField(max_length=1024, blank=True, null=True)

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.name

    @property
    def has_data(self):
        return False  # no data by default

    @property
    def size(self):
        raise NotImplementedError()


class DataObject(models.Model):
    """ implements methods and attributes for objects containing array data """
    data_size = models.IntegerField(blank=True, null=True)

    class Meta:
        abstract = True

    @property
    def has_data(self):
        return True

    @property
    def size(self):
        return self.data_size

    def compute_size(self):
        """
        :return: int - size of an object in bytes
        """
        raise NotImplementedError()

    def save(self, *args, **kwargs):
        self.data_size = self.compute_size()
        super(DataObject, self).save(*args, **kwargs)


# 2 (of 15)
class Segment(BlockBasedPermissionsMixin, BaseInfo):
    """
    NEO Segment @ G-Node.
    """
    # NEO attributes
    name = models.CharField(max_length=DEFAULTS['name_max_length'])
    filedatetime = models.DateTimeField(null=True, blank=True)
    index = models.IntegerField(null=True, blank=True)

    @property
    def size(self):
        # FIXME add other objects
        return sum([s.size for s in self.analogsignal_set.all()])


# 3 (of 15)
class EventArray(BlockBasedPermissionsMixin, BaseInfo, DataObject):
    """
    NEO EventArray @ G-Node.
    """
    name = models.CharField(max_length=DEFAULTS['name_max_length'], blank=True, null=True)

    # NEO data arrays
    labels = models.FileField(storage=fs, upload_to=make_upload_path, blank=True, null=True)
    times = models.FileField(storage=fs, upload_to=make_upload_path, blank=True, null=True)
    times__unit = TimeUnitField('times__unit', default=DEFAULTS['default_time_unit'])

    # NEO relationships
    segment = VersionedForeignKey(Segment)

    def save(self, *args, **kwargs):
        self.block = self.segment.block
        super(EventArray, self).save(*args, **kwargs)


# 4 (of 15)
class Event(BlockBasedPermissionsMixin, BaseInfo):
    """
    NEO Event @ G-Node.
    """
    # NEO attributes
    name = models.CharField(max_length=DEFAULTS['name_max_length'], blank=True, null=True)
    label = models.CharField('label', max_length=DEFAULTS['name_max_length'])
    time = models.FloatField('time')
    time__unit = TimeUnitField('time__unit', default=DEFAULTS['default_time_unit'])
    
    # NEO relationships
    segment = VersionedForeignKey(Segment)

    def save(self, *args, **kwargs):
        self.block = self.segment.block
        super(Event, self).save(*args, **kwargs)


# 5 (of 15)
class EpochArray(BlockBasedPermissionsMixin, BaseInfo, DataObject):
    """
    NEO EpochArray @ G-Node.
    """
    name = models.CharField(max_length=DEFAULTS['name_max_length'], blank=True, null=True)

    # NEO data arrays
    labels = models.FileField(storage=fs, upload_to=make_upload_path, blank=True, null=True)
    times = models.FileField(storage=fs, upload_to=make_upload_path, blank=True, null=True)
    times__unit = TimeUnitField('times__unit', default=DEFAULTS['default_time_unit'])
    durations = models.FileField(storage=fs, upload_to=make_upload_path, blank=True, null=True)
    durations__unit = TimeUnitField('durations__unit', default=DEFAULTS['default_time_unit'])

    # NEO relationships
    segment = VersionedForeignKey(Segment)

    def save(self, *args, **kwargs):
        self.block = self.segment.block
        super(EpochArray, self).save(*args, **kwargs)


# 6 (of 15)
class Epoch(BlockBasedPermissionsMixin, BaseInfo):
    """
    NEO Epoch @ G-Node.
    """
    # NEO attributes
    name = models.CharField(max_length=DEFAULTS['name_max_length'], blank=True, null=True)
    label = models.CharField('label', max_length=DEFAULTS['label_max_length'])
    time = models.FloatField('time')
    time__unit = TimeUnitField('time__unit', default=DEFAULTS['default_time_unit'])
    duration = models.FloatField('duration')
    duration__unit = TimeUnitField('duration__unit', default=DEFAULTS['default_time_unit'])
    # NEO relationships
    segment = VersionedForeignKey(Segment)

    def save(self, *args, **kwargs):
        self.block = self.segment.block
        super(Epoch, self).save(*args, **kwargs)


# 7 (of 15)
class RecordingChannelGroup(BlockBasedPermissionsMixin, BaseInfo):
    """
    NEO RecordingChannelGroup @ G-Node.
    """
    name = models.CharField(max_length=DEFAULTS['name_max_length'])


# 8 (of 15)
class RecordingChannel(BlockBasedPermissionsMixin, BaseInfo):
    """
    NEO RecordingChannel @ G-Node.
    """
    # NEO attributes
    name = models.CharField(max_length=DEFAULTS['name_max_length'])
    index = models.IntegerField('index', null=True, blank=True)

    # NEO relationships
    recordingchannelgroup = models.ManyToManyField(RecordingChannelGroup, \
                       through='recordingchannel_rcg', blank=True, null=True)

    def save(self, *args, **kwargs):
        super(RecordingChannel, self).save(*args, **kwargs)


# 9 (of 15)
class Unit(BlockBasedPermissionsMixin, BaseInfo):
    """
    NEO Unit @ G-Node.
    """
    name = models.CharField(max_length=DEFAULTS['name_max_length'])

    # NEO relationships
    recordingchannelgroup = VersionedForeignKey(RecordingChannelGroup)

    def save(self, *args, **kwargs):
        self.block = self.recordingchannelgroup.block
        super(Unit, self).save(*args, **kwargs)


# 10 (of 15)
class SpikeTrain(BlockBasedPermissionsMixin, BaseInfo, DataObject):
    """
    NEO SpikeTrain @ G-Node.
    """
    # NEO attributes
    name = models.CharField(max_length=DEFAULTS['name_max_length'], blank=True, null=True)
    t_start = models.FloatField('t_start')
    t_start__unit = TimeUnitField('t_start__unit', default=DEFAULTS['default_time_unit'])
    t_stop = models.FloatField('t_stop')
    t_stop__unit = TimeUnitField('t_stop__unit', default=DEFAULTS['default_time_unit'])

    # NEO relationships
    segment = VersionedForeignKey(Segment)
    unit = VersionedForeignKey(Unit, blank=True, null=True)

    # NEO data arrays
    times = models.FileField(storage=fs, upload_to=make_upload_path, blank=True, null=True)
    times__unit = TimeUnitField('times__unit', default=DEFAULTS['default_time_unit'])
    waveforms = models.FileField(storage=fs, upload_to=make_upload_path, blank=True, null=True)
    waveforms__unit = SignalUnitField('waveforms__unit', blank=True, null=True)

    # rewrite the size property when waveforms are supported
    def compute_size(self):
        return self.times.size

    def save(self, *args, **kwargs):
        self.block = self.segment.block
        super(SpikeTrain, self).save(*args, **kwargs)


# 11 (of 15)
class AnalogSignalArray(BlockBasedPermissionsMixin, BaseInfo, DataObject):
    """
    NEO AnalogSignalArray @ G-Node.
    """
    # NEO attributes
    name = models.CharField(max_length=DEFAULTS['name_max_length'], blank=True, null=True)
    sampling_rate = models.FloatField('sampling_rate')
    sampling_rate__unit = SamplingUnitField('sampling_rate__unit', default=DEFAULTS['default_samp_unit'])
    t_start = models.FloatField('matrix_t_start')
    t_start__unit = TimeUnitField('t_start__unit', default=DEFAULTS['default_time_unit'])

    # NEO data arrays
    signal = models.FileField(storage=fs, upload_to=make_upload_path, blank=True, null=True)
    signal__unit = SignalUnitField('signals__unit', default=DEFAULTS['default_data_unit'])

    # NEO relationships
    segment = VersionedForeignKey(Segment)
    recordingchannelgroup = VersionedForeignKey(RecordingChannelGroup, blank=True, null=True)

    def compute_size(self):
        return self.signal.size

    def save(self, *args, **kwargs):
        self.block = self.segment.block
        super(AnalogSignalArray, self).save(*args, **kwargs)


# 12 (of 15)
class AnalogSignal(BlockBasedPermissionsMixin, BaseInfo, DataObject):
    """
    NEO AnalogSignal @ G-Node.
    """
    # NEO attributes
    name = models.CharField(max_length=DEFAULTS['name_max_length'], blank=True, null=True)
    sampling_rate = models.FloatField('sampling_rate')
    sampling_rate__unit = SamplingUnitField('sampling_rate__unit', default=DEFAULTS['default_samp_unit'])
    t_start = models.FloatField('t_start')
    t_start__unit = TimeUnitField('t_start__unit', default=DEFAULTS['default_time_unit'])
    
    # NEO relationships
    segment = VersionedForeignKey(Segment)
    recordingchannel = VersionedForeignKey(RecordingChannel, blank=True, null=True)
    
    # NEO data arrays
    signal = models.FileField(storage=fs, upload_to=make_upload_path, blank=True, null=True)
    signal__unit = SignalUnitField('signal__unit', default=DEFAULTS['default_data_unit'])

    def save(self, *args, **kwargs):
        self.block = self.segment.block
        super(AnalogSignal, self).save(*args, **kwargs)


# 13 (of 15)
class IrregularlySampledSignal(BlockBasedPermissionsMixin, BaseInfo, DataObject):
    """
    NEO IrregularlySampledSignal @ G-Node.
    """
    # NEO attributes
    name = models.CharField(max_length=DEFAULTS['name_max_length'], blank=True, null=True)
    t_start = models.FloatField('t_start')
    t_start__unit = TimeUnitField('t_start__unit', default=DEFAULTS['default_time_unit'])

    # NEO relationships
    segment = VersionedForeignKey(Segment)
    recordingchannel = VersionedForeignKey(RecordingChannel, blank=True, null=True)

    # NEO data arrays
    signal = models.FileField(storage=fs, upload_to=make_upload_path, blank=True, null=True)
    signal__unit = SignalUnitField('signal__unit', default=DEFAULTS['default_data_unit'])
    times = models.FileField(storage=fs, upload_to=make_upload_path, blank=True, null=True)
    times__unit = TimeUnitField('times__unit', default=DEFAULTS['default_time_unit'])

    def full_clean(self, *args, **kwargs):
        """ Add some validation to keep 'signal' and 'times' dimensions
        consistent. Currently switched off. """
        super(IrregularlySampledSignal, self).full_clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.block = self.segment.block
        super(IrregularlySampledSignal, self).save(*args, **kwargs)


# 14 (of 15)
class Spike(BlockBasedPermissionsMixin, BaseInfo, DataObject):
    """
    NEO Spike @ G-Node.
    """
    # NEO attributes
    name = models.CharField(max_length=DEFAULTS['name_max_length'], blank=True, null=True)
    time = models.FloatField()
    time__unit = TimeUnitField('time__unit', default=DEFAULTS['default_time_unit'])
    sampling_rate = models.FloatField('sampling_rate', blank=True, null=True)
    sampling_rate__unit = SamplingUnitField('sampling_rate__unit', blank=True, null=True)
    left_sweep = models.FloatField('left_sweep', blank=True, null=True)
    left_sweep__unit = TimeUnitField('left_sweep__unit', blank=True, null=True)

    # NEO data arrays
    waveform = models.FileField(storage=fs, upload_to=make_upload_path, blank=True, null=True)
    waveform__unit = SignalUnitField('waveform__unit', default=DEFAULTS['default_data_unit'])

    # NEO relationships
    segment = VersionedForeignKey(Segment)
    unit = VersionedForeignKey(Unit, blank=True, null=True)

    def save(self, *args, **kwargs):
        self.block = self.segment.block
        super(Spike, self).save(*args, **kwargs)


class recordingchannel_rcg(VersionedM2M):
    recordingchannelgroup = VersionedForeignKey(RecordingChannelGroup)
    recordingchannel = VersionedForeignKey(RecordingChannel)
