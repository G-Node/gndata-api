from django.db import models
from state_machine.models import BaseGnodeObject
from state_machine.versioning.models import VersionedM2M
#from security import DocumentBasedPermissionsMixin
from state_machine.versioning.descriptors import VersionedForeignKey
from ephys.fields import TimeUnitField, SignalUnitField, SamplingUnitField


# TODO make nicer upload paths?

def make_upload_path(self, filename):
    """ Generates upload path for FileField """
    return "data/%s/%s" % (self.owner.username, filename)


# TODO create data and metadata connection

DEFAULTS = {
    "name_max_length": 100,
    "description_max_length": 2048,
    "label_max_length": 100,
    "unit_max_length": 10,
    "default_time_unit": "ms",
    "default_data_unit": "mV",
    "default_samp_unit": "Hz"
}


class BaseInfo(BaseGnodeObject):
    """ Base abstract class for any NEO object at G-Node """
    description = models.CharField(max_length=1024, blank=True, null=True)

    class Meta:
        abstract = True

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


# 1 (of 15)
class Block(BaseInfo):
    """
    NEO Block @ G-Node.
    """
    # NEO attributes
    name = models.CharField(max_length=DEFAULTS['name_max_length'])
    filedatetime = models.DateTimeField(null=True, blank=True)
    index = models.IntegerField(null=True, blank=True)

    @property
    def size(self):
        total = 0  # FIXME nicer way to do it in python
        for size in [s.size for s in self.segment_set.all()]:
            total += size
        return total


# 2 (of 15)
class Segment(BaseInfo):
    """
    NEO Segment @ G-Node.
    """
    # NEO attributes
    name = models.CharField(max_length=DEFAULTS['name_max_length'])
    filedatetime = models.DateTimeField(null=True, blank=True)
    index = models.IntegerField(null=True, blank=True)

    # NEO relationships
    block = VersionedForeignKey(Block, blank=True, null=True)

    @property
    def size(self):
        total = 0  # FIXME add other objects
        for size in [s.size for s in self.analogsignal_set.all()]:
            total += size
        return total


# 3 (of 15)
class EventArray(BaseInfo, DataObject):
    """
    NEO EventArray @ G-Node.
    """
    name = models.CharField(max_length=DEFAULTS['name_max_length'], blank=True, null=True)

    # NEO data arrays
    labels = models.FileField(upload_to=make_upload_path, blank=True, null=True)
    times = models.FileField(upload_to=make_upload_path)
    times__unit = TimeUnitField('times__unit', default=DEFAULTS['default_time_unit'])

    # NEO relationships
    segment = VersionedForeignKey(Segment, blank=True, null=True)


# 4 (of 15)
class Event(BaseInfo):
    """
    NEO Event @ G-Node.
    """
    # NEO attributes
    name = models.CharField(max_length=DEFAULTS['name_max_length'], blank=True, null=True)
    label = models.CharField('label', max_length=DEFAULTS['name_max_length'])
    time = models.FloatField('time')
    time__unit = TimeUnitField('time__unit', default=DEFAULTS['default_time_unit'])
    
    # NEO relationships
    segment = VersionedForeignKey(Segment, blank=True, null=True)


# 5 (of 15)
class EpochArray(BaseInfo, DataObject):
    """
    NEO EpochArray @ G-Node.
    """
    name = models.CharField(max_length=DEFAULTS['name_max_length'], blank=True, null=True)

    # NEO data arrays
    labels = models.FileField(upload_to=make_upload_path, blank=True, null=True)
    times = models.FileField(upload_to=make_upload_path)
    times__unit = TimeUnitField('times__unit', default=DEFAULTS['default_time_unit'])
    durations = models.FileField(upload_to=make_upload_path)
    durations__unit = TimeUnitField('durations__unit', default=DEFAULTS['default_time_unit'])

    # NEO relationships
    segment = VersionedForeignKey(Segment, blank=True, null=True)


# 6 (of 15)
class Epoch(BaseInfo):
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
    segment = VersionedForeignKey(Segment, blank=True, null=True)


# 7 (of 15)
class RecordingChannelGroup(BaseInfo):
    """
    NEO RecordingChannelGroup @ G-Node.
    """
    name = models.CharField(max_length=DEFAULTS['name_max_length'])

    # NEO relationships
    block = VersionedForeignKey(Block, blank=True, null=True)


# 8 (of 15)
class RecordingChannel(BaseInfo):
    """
    NEO RecordingChannel @ G-Node.
    """
    # NEO attributes
    name = models.CharField(max_length=DEFAULTS['name_max_length'])
    index = models.IntegerField('index', null=True, blank=True)

    # NEO relationships
    recordingchannelgroup = models.ManyToManyField(RecordingChannelGroup, \
                       through='recordingchannel_rcg', blank=True, null=True)


# 9 (of 15)
class Unit(BaseInfo):
    """
    NEO Unit @ G-Node.
    """
    name = models.CharField(max_length=DEFAULTS['name_max_length'])

    # NEO relationships
    recordingchannelgroup = VersionedForeignKey(RecordingChannelGroup, blank=True, null=True)


# 10 (of 15)
class SpikeTrain(BaseInfo, DataObject):
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
    segment = VersionedForeignKey(Segment, blank=True, null=True)
    unit = VersionedForeignKey(Unit, blank=True, null=True)

    # NEO data arrays
    times = models.FileField(upload_to=make_upload_path)
    times__unit = TimeUnitField('times__unit', default=DEFAULTS['default_time_unit'])
    waveforms = models.FileField(upload_to=make_upload_path, blank=True, null=True)
    waveforms__unit = SignalUnitField('waveforms__unit', blank=True, null=True)

    def get_slice(self, **kwargs):
        """ implements dataslicing/downsampling. Floats/integers are expected.
        'downsample' parameter defines the new resampled resolution.  """

        def _find_nearest(array, value):
            """ Finds index of the nearest value to the given value in the
            given array. """
            return (np.abs(array - float(value))).argmin()

        t_start = self.t_start

        # compute the boundaries if indexes are given
        s_index = kwargs.get('start_index', 0)
        e_index = kwargs.get('end_index', 10**9)

        if kwargs.has_key('samples_count'):
            if kwargs.has_key('start_time') or kwargs.has_key('start_index'):
                e_index = s_index + samples_count
            else:
                s_index = e_index - samples_count

        # need full array to compute the boundaries
        opts, timeflt = split_time( **kwargs )
        times = Datafile.objects.filter( **timeflt ).filter( local_id = self.times_id )[0].get_slice()

        if kwargs.has_key('start_time'):
            s_index = _find_nearest(times, kwargs['start_time'])
        if kwargs.has_key('end_time'):
            e_index = _find_nearest(times, kwargs['end_time'])

        if kwargs.has_key('duration'):
            duration = kwargs['duration']
            if kwargs.has_key('start_time') or kwargs.has_key('start_index'):
                e_index = _find_nearest(times, times[start_index] + duration)
            else:
                s_index = _find_nearest(times, times[end_index] + duration)

        if s_index > 0 or (e_index - s_index) < self.data_length: # slicing needed
            if s_index >= 0 and s_index < e_index:
                t_start += times[s_index] # compute new t_start
            else:
                raise IndexError("Index is out of range. From the values provided \
    we can't get the slice of the SpikeTrain. We calculated the start index as %d \
    and end index as %d. The size of the signal is %d bytes." % (s_index, e_index, \
                                                                 self.size ))

        return self.times, s_index, e_index + 1, t_start

    # rewrite the size property when waveforms are supported
    def compute_size(self):
        return self.times.size


# 11 (of 15)
class AnalogSignalArray(BaseInfo, DataObject):
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
    signal = models.FileField(upload_to=make_upload_path)
    signal__unit = SignalUnitField('signals__unit', default=DEFAULTS['default_data_unit'])

    # NEO relationships
    segment = VersionedForeignKey(Segment, blank=True, null=True)
    recordingchannelgroup = VersionedForeignKey(RecordingChannelGroup, blank=True, null=True)


# 12 (of 15)
class AnalogSignal(BaseInfo, DataObject):
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
    segment = VersionedForeignKey(Segment, blank=True, null=True)
    recordingchannel = VersionedForeignKey(RecordingChannel, blank=True, null=True)
    
    # NEO data arrays
    signal = models.FileField(upload_to=make_upload_path)
    signal__unit = SignalUnitField('signal__unit', default=DEFAULTS['default_data_unit'])

    def get_slice(self, **kwargs):
        """ implements dataslicing/downsampling. Floats/integers are expected.
        'downsample' parameter defines the new resampled resolution. hits the
        Database """
        t_start = self.t_start
        new_rate = self.sampling_rate
        data_length = len( self.signal.get_slice() ) # FIXME

        # calculate the factor to align time / sampling rate units
        factor = factor_options.get("%s%s" % (self.t_start__unit.lower(), \
                                              self.sampling_rate__unit.lower()), 1.0)

        # compute the boundaries if indexes are given
        s_index = kwargs.get('start_index', 0)
        e_index = kwargs.get('end_index', 10**9)

        samples_count = kwargs.get('samples_count', None)
        if samples_count:
            if kwargs.has_key('start_time') or kwargs.has_key('start_index'):
                e_index = s_index + samples_count
            else:
                s_index = e_index - samples_count

        if kwargs.has_key('start_time'):
            s_index = int(round(self.sampling_rate * (kwargs['start_time'] - t_start) * factor))
        if kwargs.has_key('end_time'):
            e_index = int(round(self.sampling_rate * (kwargs['end_time'] - t_start) * factor))
        duration = kwargs.get('duration', None)
        if duration:
            if kwargs.has_key('start_time') or kwargs.has_key('start_index'):
                e_index = s_index + int(round(self.sampling_rate * duration * factor))
            else:
                s_index = e_index - int(round(self.sampling_rate * duration * factor))

        if s_index > 0 or (e_index - s_index) < data_length: # slicing needed
            if s_index >= 0 and s_index < e_index:
                t_start += (s_index * 1.0 / self.sampling_rate * 1.0 / factor) # compute new t_start
            else:
                raise IndexError( "Index is out of range for an. signal %s. From the\
                    values provided we can't get the slice of the signal. We calculated the start \
                    index as %d and end index as %d. Please check those. The sampling rate is %s %s,\
                     t_start is %s %s" % (self.pk, s_index, e_index, self.sampling_rate, \
                                          self.sampling_rate__unit.lower(), self.t_start, self.t_start__unit.lower() ) )

        downsample = kwargs.get('downsample', None)
        if downsample and downsample < data_length:
            new_rate = ( float(downsample) / float( data_length ) ) * self.sampling_rate

        #opts, timeflt = split_time( **kwargs )
        #signal = Datafile.objects.filter( **timeflt ).filter( local_id = self.signal_id )[0]

        #return signal, s_index, e_index + 1, downsample, t_start, new_rate
        return s_index, e_index + 1, downsample, t_start, new_rate


# 13 (of 15)
class IrregularlySampledSignal(BaseInfo, DataObject):
    """
    NEO IrregularlySampledSignal @ G-Node.
    """
    # NEO attributes
    name = models.CharField(max_length=DEFAULTS['name_max_length'], blank=True, null=True)
    t_start = models.FloatField('t_start')
    t_start__unit = TimeUnitField('t_start__unit', default=DEFAULTS['default_time_unit'])

    # NEO relationships
    segment = VersionedForeignKey(Segment, blank=True, null=True)
    recordingchannel = VersionedForeignKey(RecordingChannel, blank=True, null=True)

    # NEO data arrays
    signal = models.FileField(upload_to=make_upload_path)
    signal__unit = SignalUnitField('signal__unit', default=DEFAULTS['default_data_unit'])
    times = models.FileField(upload_to=make_upload_path)
    times__unit = TimeUnitField('times__unit', default=DEFAULTS['default_time_unit'])

    def get_slice(self, **kwargs):
        """ implements dataslicing/downsampling. Floats/integers are expected.
        'downsample' parameter defines the new resampled resolution.  """

        def _find_nearest(array, value):
            """ Finds index of the nearest value to the given value in the
            given array. """
            return (np.abs(array - float(value))).argmin()

        t_start = self.t_start

        # compute the boundaries if indexes are given
        s_index = kwargs.get('start_index', 0)
        e_index = kwargs.get('end_index', 10**9)

        if kwargs.has_key('samples_count'):
            if kwargs.has_key('start_time') or kwargs.has_key('start_index'):
                e_index = s_index + samples_count
            else:
                s_index = e_index - samples_count

        # compute the boundaries if times are given
        opts, timeflt = split_time( **kwargs )
        times = Datafile.objects.filter( **timeflt ).filter( local_id = self.times_id )[0].get_slice()

        if kwargs.has_key('start_time'):
            s_index = _find_nearest(times, kwargs['start_time'])
        if kwargs.has_key('end_time'):
            e_index = _find_nearest(times, kwargs['end_time'])

        if kwargs.has_key('duration'):
            duration = kwargs['duration']
            if kwargs.has_key('start_time') or kwargs.has_key('start_index'):
                e_index = _find_nearest(times, times[start_index] + duration)
            else:
                s_index = _find_nearest(times, times[end_index] + duration)

        if s_index > 0 or (e_index - s_index) < self.data_length: # slicing needed
            if s_index >= 0 and s_index < e_index:
                t_start += times[s_index] # compute new t_start
            else:
                raise IndexError("Index is out of range. From the values provided \
    we can't get the slice of the signal. We calculated the start index as %d and \
    end index as %d. The size of the signal is %d bytes." % (s_index, e_index, \
                                                             self.size ))

        opts, timeflt = split_time( **kwargs )
        signal = Datafile.objects.filter( **timeflt ).filter( local_id = self.signal_id )[0].get_slice()

        downsample = kwargs.get('downsample', None)
        return self.signal, self.times, s_index, e_index + 1, downsample, t_start

    def full_clean(self, *args, **kwargs):
        """ Add some validation to keep 'signal' and 'times' dimensions
        consistent. Currently switched off. """
        #if not len( self.signal.get_slice() ) == len( self.times.get_slice() ):
        #    raise ValidationError({"Data Inconsistent": \
        #        meta_messages["data_inconsistency"]})
        super(IrregularlySampledSignal, self).full_clean(*args, **kwargs)


# 14 (of 15)
class Spike(BaseInfo, DataObject):
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
    waveform = models.FileField(upload_to=make_upload_path, blank=True, null=True)
    waveform__unit = SignalUnitField('waveform__unit', default=DEFAULTS['default_data_unit'])

    # NEO relationships
    segment = VersionedForeignKey(Segment, blank=True, null=True)
    unit = VersionedForeignKey(Unit, blank=True, null=True)


class recordingchannel_rcg(VersionedM2M):
    recordingchannelgroup = VersionedForeignKey(RecordingChannelGroup)
    recordingchannel = VersionedForeignKey(RecordingChannel)
