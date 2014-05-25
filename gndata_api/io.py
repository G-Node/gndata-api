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
    created_index = {}  # map of the temporary IDs to the newly created objects
    ever_moved = []  # collector of object IDs that ever delayed processing

    while todo:
        current = todo.pop(0)
        model_name = current.__class__.__name__.lower()
        try:
            model = EPHYS_MODELS[model_name]
        except KeyError:
            raise TypeError("Class %s is not supported" % model_name)

        # parse parents
        fk_fields = get_fk_field_names(model)
        parents = [(name, getattr(current, name, None)) for name in fk_fields]
        parents = filter(lambda x: x[1] is not None, parents)

        try:
            fk_kwargs = dict([(k, created_index[id(v)]) for k, v in parents])
        except KeyError:
            todo.append(current)
            if id(current) in ever_moved:
                raise IOError(
                    'Object %s has improperly defined parents' % str(current)
                )

            ever_moved.append(id(current))
            continue  # parent object is not created yet, delay

        # parse simple fields with or without units
        simple_fields = get_simple_field_names(model)

        get_val = lambda obj, name: getattr(obj, name, None)
        get_unit = lambda obj, name: \
            getattr(obj, name.replace('__unit', '')).dimensionality.string.replace('dimensionless', 'empty')
        parse_simple = lambda obj, name: \
            get_unit(obj, name) if name.find('__unit') > 0 else get_val(obj, name)

        values = [(name, parse_simple(current, name)) for name in simple_fields]
        values = [(k, v.item() if hasattr(v, 'dimensionality') else v) for k, v in values]
        simple_kwargs = dict(filter(lambda x: x[1] is not None, values))

        # parse array fields
        temp_paths = []  # collector of temp data files
        data_kwargs = {}

        data_fields = get_data_field_names(model)
        raw_arrays = [(name, get_array(current, name)) for name in data_fields]

        for name, array in raw_arrays:

            filename = uuid.uuid1().hex + ".h5"
            path = os.path.join(tmp.gettempdir(), filename)

            with h5py.File(path, 'w') as temp_f:
                temp_f.create_dataset(name=str(id(current)), data=array)

            data_kwargs[name] = File(open(path), name=filename)
            if hasattr(array, 'dimensionality'):
                data_kwargs[name + '__unit'] = \
                    array.dimensionality.string.replace('dimensionless', 'empty')

            temp_paths.append(path)

        params = dict(simple_kwargs.items() + fk_kwargs.items() + data_kwargs.items())
        params['owner'] = owner
        if model_name == 'recordingchannel':  # FIXME workaround for m2ms
            params['block'] = created_index[id(current.recordingchannelgroups[0].block)]

        local_obj = model.objects.create(**params)
        created_index[id(current)] = local_obj

        for path in temp_paths:
            os.remove(path)

        # children
        reverse_models = get_reverse_models(model)
        reverse_names = [m.__name__.lower() + 's' for m in reverse_models]
        if model_name == 'recordingchannelgroup':  # FIXME workaround for m2ms
            reverse_names.append('recordingchannels')
        children = [getattr(current, name, None) for name in reverse_names]
        children = filter(lambda x: x is not None and len(x) > 0, children)
        children = filter(lambda x: id(x) not in created_index.keys(), children)

        todo += [item for sublist in children for item in sublist]

    return created_index[id(neo_obj)]