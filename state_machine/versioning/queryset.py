from django.utils import timezone

from django.db import connection, transaction
from django.db.models.query import QuerySet, ValuesQuerySet, ValuesListQuerySet, DateQuerySet
from django.db.models.sql.where import AND

from django.db.models import Q

from gndata_api.utils import *


#===============================================================================
# VERSIONED QuerySets
#===============================================================================

class QuerySetMixin(object):
    """ basic extension for every queryset class to support versioning """
    _at_time = None  # proxy version time for related models
    _time_injected = False

    def inject_time(self):
        """ pre-processing versioned queryset before evaluating against database 
        back-end. Inject version time filters for every versioned model (table),
        used in the query. """
        def update_constraint(node, table):
            if hasattr(node, 'children') and node.children:
                for child in node.children:
                    update_constraint(child, table)
            else:
                node[0].alias = table

        def extract_rel_tables(nodes, extracted):
            for name, inside in nodes.items():
                extracted.append(name)
                if inside:
                    extract_rel_tables(inside, extracted)

        if not self._time_injected:
            # 1. save limits
            high_mark, low_mark = self.query.high_mark, self.query.low_mark

            # 2. clear limits to be able to assign more filters, see
            # 'can_filter()'
            self.query.clear_limits()

            # 3. update time filters:
            # - create time filters as separate where node
            qry = self.query.__class__(model=self.model)
            if self._at_time:
                at_time = self._at_time
                qry.add_q(Q(starts_at__lte = at_time))
                qry.add_q(Q(ends_at__gt = at_time) | Q(ends_at__isnull = True))
            else:
                qry.add_q(Q(ends_at__isnull = True))

            cp = self.query.get_compiler(using=self.db)
            cp.pre_sql_setup()  # thanks god I found that
            tables = [table for table, rc in cp.query.alias_refcount.items() if rc]

            # - build map of models with tables: {<table name>: <model>}
            vmodel_map = {}
            for model in connection.introspection.installed_models(tables):
                vmodel_map[model._meta.db_table] = model

            # - add node with time filters to all versioned models (tables)
            for table in tables:
                # find real table name, not alias
                real_name = table
                for mod_name, aliases in self.query.table_map.items():
                    if table in aliases:
                        real_name = mod_name

                # skip non-versioned models,like User: no need to filter by time
                if vmodel_map.has_key(real_name):
                    superclasses = vmodel_map[real_name].mro()
                    cls_names = [x.__name__ for x in superclasses]
                    if not ('ObjectState' in cls_names or 'VersionedM2M' in cls_names):
                        continue

                cloned_node = qry.where.__deepcopy__(memodict=None)
                update_constraint(cloned_node, table)
                self.query.where.add(cloned_node, AND)

            # 4. re-set limits
            self.query.set_limits(low=low_mark, high=high_mark)
            self._time_injected = True

    def _filter_or_exclude(self, negate, *args, **kwargs):
        """ versioned QuerySet supports 'at_time' parameter for filtering 
        versioned objects. """
        kwargs, timeflt = split_time(**kwargs)
        if timeflt.has_key('at_time'):
            self._at_time = timeflt['at_time']
        return super(QuerySetMixin, self)._filter_or_exclude(negate, *args, **kwargs)

    def _clone(self, klass=None, setup=False, **kwargs):
        """ override _clone method to preserve 'at_time' attribute while cloning
        queryset - in stacked filters, excludes etc. """
        #kwargs['_at_time'] = self._at_time # an alternative way of saving time
        c = super(QuerySetMixin, self)._clone(klass, setup, **kwargs)
        c._at_time = self._at_time
        c._time_injected = self._time_injected
        return c

    def iterator(self):
        """ need to inject version time before executing against database """
        self.inject_time()
        for obj in super(QuerySetMixin, self).iterator():
            yield obj

    def count(self):
        """ need to inject version time (or ends_at = NULL) before executing 
        against database. No tables are in alias_refcount if no other filters 
        are set, so the time injection doesn't work.. workaround here: inject a 
        meaningless filter, which doesn't change the *count* query. """
        q = self.filter(pk__gt=0)
        q.inject_time()
        return super(QuerySetMixin, q).count()

    def delete(self):
        """ deletion for versioned objects means setting the 'ends_at' field 
        to the current datetime. Applied only for active versions, having 
        ends_at=NULL """
        now = timezone.now()

        # select active records
        active = self.filter(ends_at__isnull=True)

        # delete records - this is the standard QuerySet update call
        super(QuerySetMixin, active).update(ends_at=now)

    def exists(self):
        """ exists if there is at least one record with ends_at = NULL """
        q = self.filter(ends_at__isnull=True)
        q.inject_time()
        return super(QuerySetMixin, q).exists()

    def in_bulk(self):
        raise NotImplementedError("Not implemented for versioned objects")


class M2MQuerySet(QuerySetMixin, QuerySet):
    pass


class VersionedValuesQuerySet(QuerySetMixin, ValuesQuerySet):
    pass


class VersionedValuesListQuerySet(QuerySetMixin, ValuesListQuerySet):
    pass


class VersionedDateQuerySet(QuerySetMixin, DateQuerySet):
    pass


class VersionedQuerySet(QuerySetMixin, QuerySet):
    """ An extension for a core QuerySet that supports versioning by overriding 
    some key functions, like create etc. """

    def _clone(self, klass=None, setup=False, **kwargs):
        """ need to use versioned classes for values, value list and dates """
        if klass == ValuesQuerySet:
            klass = VersionedValuesQuerySet
        elif klass == ValuesListQuerySet:
            klass = VersionedValuesListQuerySet
        elif klass == DateQuerySet:
            klass = VersionedDateQuerySet
        return super(VersionedQuerySet, self)._clone(klass, setup, **kwargs)

    def iterator(self):
        """ we assign a special attribute '_at_time' for every object if the 
        original query was supposed to return older versions from some time in 
        the past ('_at_time' was specified in the Request). This is useful 
        primarily to proxy this time to related managers to get related objects
        from the same time, as well as indicates that a different version from 
        the current of an object was requested. """
        for obj in super(VersionedQuerySet, self).iterator():
            if self._at_time:
                obj._at_time = self._at_time
            yield obj

    def bulk_create(self, objs, batch_size=None):
        """ wrapping around a usual bulk_create to provide version-specific 
        information for all objects. ITERATES over all objects and saves them
        correctly (slow). As with original bulk creation, reverse relationships
        and M2Ms are not supported. WARNING: has side-effects"""
        with transaction.commit_on_success_unless_managed(using=self.db):
            for obj in objs:
                obj.save()

    def update(self, **kwargs):
        """ update objects with new attrs and FKs """
        if kwargs:
            objs = self._clone()
            for obj in objs:
                for name, value in kwargs.items():
                    setattr(obj, name, value)
            return self.bulk_create(objs)
        return self

    def delete(self):
        """ a special versioned delete, which removes appropriate direct and 
        reversed m2ms relations for the objects that are going to be deleted """
        super(VersionedQuerySet, self).delete()

        # TODO check whether related m2m are correctly deleted

        # TODO check whether it's needed to update child FKs

        """
        now = timezone.now()
        pks = list(self.values_list('pk', flat=True))  # ids of main objects

        # delete all directly related m2ms
        for m2m_field in self.model._meta.many_to_many:
            filt = {}
            filt[m2m_field.m2m_field_name() + '_id__in'] = pks
            filt['ends_at__isnull'] = True
            m2m_field.rel.through.objects.filter(**filt).update(ends_at = now)

        # delete all reversly related m2ms
        rel_objs = self.model._meta.get_all_related_objects()
        reverse_related = [x for x in rel_objs if 'VersionedM2M' in \
                                                  [cls.__name__ for cls in x.model.mro()]]
        for m2m_related in reverse_related:
            filt = {}
            filt[m2m_related.field.name + '_id__in'] = pks
            filt['ends_at__isnull'] = True
            m2m_related.model.objects.filter(**filt).update(ends_at = now)
        """

    def get_by_guid(self, guid):
        """ every object has a global ID (basically it's a hash of it's JSON 
        representation). As this ID is unique, one can request an object by it's
        GUID directly."""
        return self.get(guid=guid)