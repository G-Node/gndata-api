from django.db import models

from queryset import VersionedQuerySet, M2MQuerySet
from gndata_api.utils import *


class VersionManager(models.Manager):
    """ A special manager for versioned objects. By default it returns queryset 
    with filters on the 'ends_at' attribute = NULL (last version of an object). 
    If 'at_time' is provided, i.e. the special version of an object is 
    requested, this manager returns queryset tuned to the provided time. The 
    'at_time' parameter should be provided to the manager at first call with the
    filter() method of this Manager. """
    use_for_related_fields = True
    _at_time = None

    def all(self):
        """ need to proxy all() to apply versioning filters """
        return self.get_query_set().all()

    def filter(self, **kwargs):
        """ method is overriden to support object versions. If an object is 
        requested at a specific point in time here we split this time from 
        kwargs to further proxy it to the QuerySet, so an appropriate version is
        fetched. """
        kwargs, timeflt = split_time(**kwargs)
        return self.get_query_set(**timeflt).filter(**kwargs)

    def proxy_time(self, proxy_to, **timeflt):
        if timeflt.has_key('at_time'):
            proxy_to._at_time = timeflt['at_time']
        elif self._at_time:
            proxy_to._at_time = self._at_time
        return proxy_to


class VersionedM2MManager(VersionManager):
    """ A manager for versioned relations. Used to proxy a special subclass of 
    the Queryset (M2MQuerySet) designed for M2M relations. """

    def get_queryset(self, **timeflt):
        """ init QuerySet that supports m2m relations versioning """
        qs = M2MQuerySet(self.model, using=self._db)
        self.proxy_time(qs, **timeflt)
        return qs


class VersionedObjectManager(VersionManager):
    """ extends a normal manager for versioned-type objects """

    def get_queryset(self, **timeflt):
        """ init QuerySet that supports object versioning """
        qs = VersionedQuerySet(self.model, using=self._db)
        self.proxy_time(qs, **timeflt)
        return qs

    def get_by_guid(self, guid):
        """ proxy get_by_guid() method to QuerySet """
        return self.get_query_set().get_by_guid(guid)
