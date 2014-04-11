from django.db import connection, transaction
from django.db.models.query import QuerySet
from django.db.models import sql
from django.db.models import Q
from django.utils import timezone

from gndata_api.utils import *
from deletion import VersionedCollector

import uuid

#===============================================================================
# VERSIONED QuerySets
#===============================================================================


class VersionedQuerySet(QuerySet):
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

        if self._time_injected:
            return

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
            self.query.where.add(cloned_node, sql.where.AND)

        # 4. re-set limits
        self.query.set_limits(low=low_mark, high=high_mark)
        self._time_injected = True

    def _filter_or_exclude(self, negate, *args, **kwargs):
        """ versioned QuerySet supports 'at_time' parameter for filtering 
        versioned objects. """
        kwargs, timeflt = split_time(**kwargs)
        if timeflt.has_key('at_time'):
            self._at_time = timeflt['at_time']
        return super(VersionedQuerySet, self)._filter_or_exclude(negate, *args, **kwargs)

    def _clone(self, klass=None, setup=False, **kwargs):
        """ override _clone method to preserve 'at_time' attribute while cloning
        queryset - in stacked filters, excludes etc. """
        #kwargs['_at_time'] = self._at_time # an alternative way of saving time
        c = super(VersionedQuerySet, self)._clone(klass, setup, **kwargs)
        c._at_time = self._at_time
        c._time_injected = self._time_injected
        return c

    def iterator(self):
        """ need to inject version time before executing against database.
        It assigns a special attribute '_at_time' for every object if the
        original query was supposed to return older versions from some time in
        the past ('_at_time' was specified in the Request). This is useful
        primarily to proxy this time to related managers to get related objects
        from the same time, as well as indicates that a different version from
        the current of an object was requested. """
        self.inject_time()
        for obj in super(VersionedQuerySet, self).iterator():
            if self._at_time:
                obj._at_time = self._at_time
            yield obj

    def bulk_create(self, objs, batch_size=None):
        """ wrapping around a usual bulk_create to provide version-specific
        information for all objects. As with original bulk creation, reverse
        relationships and M2Ms are not supported. DOES set the PRIMARY KEY for
        new objects, updates PK and creation modification dates for existing
        objects. Works with BaseVersionedObject's only.

        WARNING: has side-effects """
        def close_records(ids_to_close):
            query = sql.UpdateQuery(self.model)

            pk_field = query.get_meta().pk
            query.add_update_values({'ends_at': now})
            query.where = query.where_class()
            constr = sql.where.Constraint(None, pk_field.column, pk_field)
            query.where.add((constr, 'in', ids_to_close), sql.where.AND)
            query.add_q(Q(ends_at__isnull=True))
            query.get_compiler(self.db).execute_sql(None)

        assert batch_size is None or batch_size > 0

        if self.model._meta.parents:
            raise ValueError("Can't bulk create an inherited model")

        if not objs:
            return objs

        now = timezone.now()
        ids_to_close = []
        for obj in objs:  # this loop modifies given objects

            if obj.pk:  # existing object, need to "close" old version later
                ids_to_close.append(obj.pk)

            else:  # new object
                obj.pk = get_new_local_id()
                obj.date_created = now

            obj.starts_at = now
            obj.guid = uuid.uuid1().hex

        self._for_write = True
        fields = self.model._meta.local_fields
        with transaction.commit_on_success_unless_managed(using=self.db):

            # close old records by setting 'ends_at' to 'now', must be first
            close_records(ids_to_close)

            # insert records with new / updated objects
            self._batched_insert(list(objs), fields, batch_size)

        return objs

    def update(self, **kwargs):
        """ update objects with new attrs and FKs """
        assert self.query.can_filter(), \
            "Cannot update a query once a slice has been taken."

        if kwargs:
            objs = self._clone()
            for obj in objs:
                for name, value in kwargs.items():
                    setattr(obj, name, value)
            return self.bulk_create(objs)
        return self

    def delete(self):
        """ a special versioned delete, which removes appropriate direct and
        reversed m2ms relations for the objects that are going to be deleted.
        Subclasses the delete operation to use different Collector """

        assert self.query.can_filter(), \
            "Cannot use 'limit' or 'offset' with delete."

        # select active records
        active = self.filter(ends_at__isnull=True)
        del_query = active._clone()

        # The delete is actually 2 queries - one to find related objects,
        # and one to delete. Make sure that the discovery of related
        # objects is performed on the same database as the deletion.
        del_query._for_write = True

        # Disable non-supported fields.
        del_query.query.select_for_update = False
        del_query.query.select_related = False
        del_query.query.clear_ordering(force_empty=True)

        collector = VersionedCollector(using=del_query.db)
        collector.collect(del_query)
        collector.delete()

        # Clear the result cache, in case this QuerySet gets reused.
        self._result_cache = None

    def count(self):
        """ need to inject version time (or ends_at = NULL) before executing
        against database. No tables are in alias_refcount if no other filters
        are set, so the time injection doesn't work.. workaround here: inject a
        meaningless filter, which doesn't change the *count* query. """
        q = self.filter()
        q.inject_time()
        return super(VersionedQuerySet, q).count()

    def exists(self):
        """ exists if there is at least one record with ends_at = NULL """
        q = self.filter()
        q.inject_time()
        return super(VersionedQuerySet, q).exists()

    def in_bulk(self):
        raise NotImplementedError("Not implemented for versioned objects")
