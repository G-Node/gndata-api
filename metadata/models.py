from django.db import models
from django.utils import timezone
from state_machine.models import BaseGnodeObject, PermissionsBase
from state_machine.versioning.descriptors import VersionedForeignKey


class Reporter(BaseGnodeObject, PermissionsBase):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField()
    file = models.FileField(blank=True, null=True, upload_to='/tmp')

    def __unicode__(self):
        return u"%s %s" % (self.first_name, self.last_name)


class Article(BaseGnodeObject):
    headline = models.CharField(max_length=100)
    pub_date = models.DateField(default=timezone.now())
    reporter = VersionedForeignKey(Reporter)

    def __unicode__(self):
        return self.headline

    class Meta:
        ordering = ('headline',)