from operator import attrgetter

from django.db import transaction
from django.db.models import signals, sql
from django.db.models.deletion import Collector
from django.utils import timezone, six


class VersionedCollector(Collector):

    def delete(self):
        """ deletion for versioned objects means setting the 'ends_at' field
        to the current datetime. Applied only for active versions, having
        ends_at=NULL """
        now = timezone.now()

        # sort instance collections
        for model, instances in self.data.items():
            self.data[model] = sorted(instances, key=attrgetter("pk"))

        # if possible, bring the models in an order suitable for databases that
        # don't support transactions or cannot defer constraint checks until the
        # end of a transaction.
        self.sort()

        with transaction.commit_on_success_unless_managed(using=self.using):
            # send pre_delete signals
            for model, obj in self.instances_with_model():
                if not model._meta.auto_created:
                    signals.pre_delete.send(
                        sender=model, instance=obj, using=self.using
                    )

            # fast deletes - TODO check works correctly with versioned rels
            for qs in self.fast_deletes:
                query = sql.UpdateQuery(qs.model)
                pk_list = [obj.pk for obj in qs.all()]
                query.update_batch(pk_list, {'ends_at': now}, self.using)

            # update fields - TODO check works correctly with versioned rels
            for model, instances_for_fieldvalues in six.iteritems(self.field_updates):
                for (field, value), instances in six.iteritems(instances_for_fieldvalues):
                    for o in instances:  # update FK fields
                        setattr(o, field.name, value)
                    model.objects.bulk_create(instances)

            # reverse instance collections
            for instances in six.itervalues(self.data):
                instances.reverse()

            # delete instances by setting 'ends_at' to 'now'
            for model, instances in six.iteritems(self.data):
                query = sql.UpdateQuery(model)
                pk_list = [obj.pk for obj in instances]
                query.update_batch(pk_list, {'ends_at': now}, self.using)

                if not model._meta.auto_created:
                    for obj in instances:
                        signals.post_delete.send(
                            sender=model, instance=obj, using=self.using
                        )

        # update collected instances
        for model, instances_for_fieldvalues in six.iteritems(self.field_updates):
            for (field, value), instances in six.iteritems(instances_for_fieldvalues):
                for obj in instances:
                    setattr(obj, field.attname, value)
        for model, instances in six.iteritems(self.data):
            for instance in instances:
                setattr(instance, model._meta.pk.attname, None)