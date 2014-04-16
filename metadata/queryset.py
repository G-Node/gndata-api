from state_machine.versioning.queryset import VersionedQuerySet
from state_machine.versioning.managers import VersionedObjectManager


class SectionQuerySet(VersionedQuerySet):

    def create(self, **kwargs):
        # this method uses obj.save() to create, which is overloaded in the
        # Section model and implements required validation rules already
        return super(SectionQuerySet, self).create(**kwargs)

    def update(self, **kwargs):
        objs = self._clone().all()

        if len(objs) > 1:  # bulk updates are not allowed
            raise ValueError("bulk updates are not allowed.")

        if len(objs) == 0:
            return

        obj = objs[0]
        test = lambda x: (not x.primary_key) and x.editable
        allowed = [f.name for f in self.model._meta.local_fields if test(f)]

        if kwargs:
            for name, value in kwargs.items():
                if name in allowed:
                    setattr(obj, name, value)

        obj.save()  # save method implements required validation rules already


class SectionManager(VersionedObjectManager):
    """ extends a normal manager to supply Section-specific queryset """

    def get_queryset(self, **timeflt):
        """ init QuerySet that supports object versioning """
        qs = SectionQuerySet(self.model, using=self._db)
        self.proxy_time(qs, **timeflt)
        return qs