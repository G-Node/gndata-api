import tempfile as tmp

from django.core.files import File
from ephys.models import *
from utils import *

EPHYS_MODELS = {
    'block': Block,
    'segment': Segment,
    'eventarray': EventArray,
    'event': Event,
    'epocharray': EpochArray,
    'epoch': Epoch,
    'recordingchannelgroup': RecordingChannelGroup,
    'recordingchannel': RecordingChannel,
    'unit': Unit,
    'spiketrain': SpikeTrain,
    'analogsignalarray': AnalogSignalArray,
    'analogsignal': AnalogSignal,
    'irregularlysampledsignal': IrregularlySampledSignal,
    'spike': Spike,
}


def import_neo(neo_obj, owner):
    """
    Parses a given Neo object and creates appropriate local object structure.

    :param neo_obj:     an instance of Neo object
    :param owner:       a django-user to assign new object to
    :return:            top new django-object created
    """

    def is_parent(model_name):
        return model_name in ('block', 'segment', 'recordingchannelgroup',
                              'recordingchannel', 'unit')

    def get_array(obj, field_name):
        model_name = obj.__class__.__name__.lower()

        is_array_1 = field_name == "signal" and model_name in \
            ('analogsignal', 'analogsignalarray', 'irregularlysampledsignal')
        is_array_2 = field_name == "times" and model_name == 'spiketrain'

        if is_array_1 or is_array_2:
            return obj
        elif hasattr(obj, field_name):
            return getattr(obj, field_name, None)

    todo = [neo_obj]  # array of objects to import
    parent_index = {}  # map of the temporary IDs to the newly created objects

    while todo:
        current = todo[0]
        model_name = current.__class__.__name__.lower()
        try:
            model = EPHYS_MODELS[model_name]
        except KeyError:
            raise TypeError("Class %s is not supported" % model_name)

        # simple fields with or without units
        simple_fields = get_simple_field_names(model)

        get_val = lambda obj, name: getattr(obj, name, None)
        get_unit = lambda obj, name: \
            getattr(obj, name.replace('__unit', '')).dimensionality.string
        parse_simple = lambda obj, name: \
            get_val(obj, name) if name.find('__unit') > 0 else get_unit(obj, name)

        values = [(name, parse_simple(current, name)) for name in simple_fields]
        simple_kwargs = dict(filter(lambda x: x[1] is not None, values))

        # parents
        fk_fields = get_fk_field_names(model)
        parents = [(name, getattr(current, name, None)) for name in fk_fields]
        parents = filter(lambda x: x[1] is not None, parents)

        fk_kwargs = dict([(k, parent_index[id(v)]) for k, v in parents])

        # array fields
        temp_paths = []  # collector of temp data files
        data_kwargs = {}

        data_fields = get_data_field_names(model)
        raw_arrays = [(name, get_array(current, name)) for name in data_fields]

        for name, array in raw_arrays:

            filename = uuid.uuid1().hex + ".h5"
            path = os.path.join(tmp.gettempdir(), filename)

            with h5py.File(path, 'w') as temp_f:
                temp_f.create_dataset(name=id(current), data=array)

            data_kwargs[name] = File(open(path), name=filename)
            if hasattr(array, 'dimensionality'):
                data_kwargs[name + '__unit'] = array.dimensionality.string

            temp_paths.append(path)

        params = dict(simple_kwargs.items() + fk_kwargs.items() + data_kwargs.items())
        params['owner'] = owner

        local_obj = model.objects.create(**params)

        # add object to parent_index
        if is_parent(model_name):
            parent_index[id(current)] = local_obj

        for path in temp_paths:
            os.remove(path)

        # children
        reverse_models = get_reverse_models(model)
        reverse_names = [m.__name__.lower() + 's' for m in reverse_models]
        children = [getattr(current, name, None) for name in reverse_names]
        children = filter(lambda x: x is not None and type(x) == list, children)

        todo += [item for sublist in children for item in sublist]

    return parent_index[id(neo_obj)]