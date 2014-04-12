from gndata_api import settings

max_results = settings.REST_CONFIG['max_results']


class BaseService(object):
    """
    An abstract class that implements basic Service functions like get single
    object, get list of objects, create, update and delete objects.

    Assumes a model subclasses an BaseGnodeObject.
    """
    def __init__(self, model):
        self.model = model

    def list(self, user, filters=[], excludes=[], max_results=max_results, offset=0):
        """
        List of objects filtered with filters and negative filters (excludes).

        :param filters:     list of filters to apply
        :type filters:      [('key1', 'value1'), ('key1', 'value1'), ...]
        :param excludes:    list of negative filters
        :type excludes:     [('key1', 'value1'), ('key1', 'value1'), ...]

        :returns: list of objects of type self.model
        """
        objects = self.model.objects.all()

        if hasattr(self.model, 'security_filter'):
            objects = self.model.security_filter(objects, user)
        else:
            objects = objects.filter(owner=user)

        # processing one-by-one, potentially equal keys (m2m, metadata)
        for filt in filters:
            filter_dict = dict([filt])
            objects = objects.filter(**filter_dict)

        for filt in excludes:
            filter_dict = dict([filt])
            objects = objects.exclude(**filter_dict)

        return objects.distinct()[offset: offset + max_results]

    def get(self, user, pk, at_time=None):
        """
        Get a single object, if accessible for the user.
        Raises ReferenceError if objects do not support access management.

        :returns: single object of type self.model
        """
        qs = self.model.objects.filter()

        if at_time:
            qs = qs.filter(at_time=at_time)

        obj = qs.get(pk=pk)
        if not hasattr(obj, 'is_accessible') or not obj.is_accessible(user):
            raise ReferenceError('You are not authorized to access this object')

        return obj

    def create(self, user, obj):
        """
        Creates an object using given object as a template.
        Does not modify the given object.

        :returns: created object of type self.model
        """
        fields = [f for f in obj._meta.local_fields if not f.primary_key]
        params = dict([(f.name, getattr(obj, f.name)) for f in fields])
        params['owner'] = user
        return self.model.objects.create(**params)

    def update(self, user, pk, obj):
        """
        Updates an object with primary key PK using given object as a template.
        Validates if a user can modify this object.
        Does not modify the given object.

        :returns: updated object of type self.model
        """
        fresh = self.model.objects.get(pk=pk)
        if not hasattr(fresh, 'is_editable') or not fresh.is_editable(user):
            raise ReferenceError('You are not authorized to change this object')

        qs = self.model.objects.filter(pk=pk)
        test = lambda x: not x.primary_key and x.editable
        fields = [f for f in obj._meta.local_fields if test(f)]
        params = dict([(f.attname, getattr(obj, f.attname)) for f in fields])
        return qs.update(**params)[0]

    def delete(self, user, pk):
        """
        Deletes an object with primary key PK.
        Validates if a user can modify this object.
        """
        obj = self.model.objects.get(pk=pk)
        if not hasattr(obj, 'is_editable') or not obj.is_editable(user):
            raise ReferenceError('You are not authorized to change this object')

        obj.delete()