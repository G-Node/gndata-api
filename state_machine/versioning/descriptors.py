from django.db.models.fields.related import ReverseSingleRelatedObjectDescriptor
from django.db.models.fields.related import ManyRelatedObjectsDescriptor
from django.db.models.fields.related import ReverseManyRelatedObjectsDescriptor
from django.db import models

#===============================================================================
# Descriptor subclasses for VERSIONED relationships
#===============================================================================


class VReverseSingleRelatedObjectDescriptor(ReverseSingleRelatedObjectDescriptor):
    """ To natively support versioned objects, we need to proxy object's time
    ('_at_time') parameter across object descriptors. To fetch related objects 
    at the time, equal to the time of the original object, the corresponding 
    QuerySet should be interfaced as VersionedQuerySet with '_at_time' parameter
    equal to the the original object '_at_time'. So we do need to override the
    'get_query_set' method only. """

    def get_queryset(self, **db_hints):
        qs = super(VReverseSingleRelatedObjectDescriptor,
                   self).get_queryset(**db_hints)

        # assign _at_time to the qs if needed
        if db_hints.has_key('instance'):
            if isinstance(db_hints['instance'], self.field.model):
                inst = db_hints['instance']
                if hasattr(inst, '_at_time'):
                    at_time = inst._at_time
                    if at_time:
                        qs._at_time = at_time
        return qs


class VManyRelatedObjectsDescriptor(ManyRelatedObjectsDescriptor):

    def related_manager_cls(self):
        # one can do some monkey patching here
        return super(VManyRelatedObjectsDescriptor, self).related_manager_cls()


class VReverseManyRelatedObjectsDescriptor(ReverseManyRelatedObjectsDescriptor):

    def related_manager_cls(self):
        # one can do some monkey patching here
        return super(VReverseManyRelatedObjectsDescriptor, self).related_manager_cls()

#===============================================================================
# Field subclasses for VERSIONED relationships
#===============================================================================


class VersionedForeignKey(models.ForeignKey):

    def __init__(self, *args, **kwargs):
        super(VersionedForeignKey, self).__init__(*args, **kwargs)
        self.db_constraint = False


class VersionedManyToManyField(models.ManyToManyField):

    def __init__(self, *args, **kwargs):
        super(VersionedManyToManyField, self).__init__(*args, **kwargs)
        self.db_constraint = False