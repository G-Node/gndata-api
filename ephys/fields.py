from django.db import models
from django import forms

UNIT_TYPES = {
    "time": ("s", "ms", "us"),  # *1000, *1, /1000
    "signal": ("V", "mV", "uV"),
    "sampling": ("Hz", "kHz", "MHz")  # *1, *1000, *100000, *1
}


class UnitField(models.CharField):
    """
    This field is going to store a unit of any measure.
    """
    __metaclass__ = models.SubfieldBase
    _unit_type = None
    empty_strings_allowed = False

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 10
        super(UnitField, self).__init__(*args, **kwargs)

    def validate(self, value, model_instance):
        super(UnitField, self).validate(value, model_instance)
        if self._unit_type and (not value in UNIT_TYPES[self._unit_type]):
            raise forms.ValidationError(
                "Unit provided is not supported: %s. Use: %s." %
                (value, UNIT_TYPES)
            )


class TimeUnitField(UnitField):
    """ This field should store time units. """
    def __init__(self, *args, **kwargs):
        super(TimeUnitField, self).__init__(*args, **kwargs)
        self._unit_type = 'time'


class SignalUnitField(UnitField):
    """ This field stores signal units. """
    def __init__(self, *args, **kwargs):
        super(SignalUnitField, self).__init__(*args, **kwargs)
        self._unit_type = 'signal'


class SamplingUnitField(UnitField):
    """ This field stores sampling rate units. """
    def __init__(self, *args, **kwargs):
        super(SamplingUnitField, self).__init__(*args, **kwargs)
        self._unit_type = 'sampling'
