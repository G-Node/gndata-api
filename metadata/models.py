from django.db import models
from django.utils import timezone
from state_machine.models import BaseGnodeObject, PermissionsBase
from state_machine.versioning.descriptors import VersionedForeignKey


class Document(BaseGnodeObject, PermissionsBase):
    """
    Class represents a metadata "Document".
    """

    # odML fields
    author = models.CharField(max_length=100, blank=True, null=True)
    date = models.DateField(null=True)
    version = models.CharField(max_length=100, blank=True, null=True)
    repository = models.CharField(max_length=100, blank=True, null=True)


class Section(BaseGnodeObject):
    """
    Class represents a metadata "Section". Used to organize metadata
    (properties - values), Datafiles and NEO Blocks in a tree-like structure.
    May be recursively linked to itself. May be made public or shared with
    specific users.
    """

    # odML fields
    name = models.CharField(max_length=100, blank=True, null=True)
    type = models.CharField(max_length=50, blank=True, null=True)
    reference = models.CharField(max_length=100, blank=True, null=True)
    definition = models.CharField(max_length=100, blank=True, null=True)
    link = models.CharField(max_length=100, blank=True, null=True)
    include = models.CharField(max_length=100, blank=True, null=True)
    repository = models.CharField(max_length=100, blank=True, null=True)
    mapping = models.CharField(max_length=100, blank=True, null=True)
    section = VersionedForeignKey('self', blank=True, null=True, related_name='parent_section')
    document = VersionedForeignKey(Document, blank=True, null=True)

    # position in the list on the same level in the tree
    tree_position = models.IntegerField(default=0)
    # field indicates whether it is a "template" section
    is_template = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return 'section_details', [self.local_id_as_str]

    @property
    def sections(self):
        return self.section_set.order_by("-tree_position")

    def fetch_deep_ids(self, ids):
        """ return all section ids located inside sections with given ids. This
        function as many sql calls as there are levels of the section tree """
        qs = self.__class__.objects.filter(parent_section_id__in=ids)
        down_one_level = list(qs.values_list('pk', flat=True))
        if down_one_level:
            return ids + self.fetch_deep_ids(down_one_level)
        return ids

    def stats(self, cascade=False):
        """ Section statistics """
        sec_ids = [self.pk]
        if cascade:  # recursively traverse a tree of child sections
            sec_ids = self.fetch_deep_ids(sec_ids)

        stats = {}  # calculate section statistics
        for rm in self._meta.get_all_related_objects():
            if not rm.model == self.__class__:
                kwargs = {rm.field.name + '_id__in': sec_ids}
                v = rm.model.objects.filter(**kwargs).count()
            else:
                v = len(sec_ids) - 1  # exclude self

            stats[rm.name] = v

        return stats

    def _get_next_tree_pos(self):
        """ Returns the next tree index "inside" self. """
        if self.sections:
            return int(self.sections[0].tree_position) + 1
        return 1

    def save(self, *args, **kwargs):
        def obj_has_changed(old, new):
            return (old is None and new is not None) or \
                   (new is None and old is not None) or \
                   (old is not None and new is not None and not old.pk == new.pk)

        # TODO implement the same logic in QuerySet for safety

        if self.pk is not None:  # update case
            old = self.__class__.objects.get(pk=self.pk)
            if obj_has_changed(old.document, self.document):
                if obj_has_changed(old.section, self.section):
                    self.section = old.section

                if not old.section is None:
                    raise ValueError("Clean parent section to change Document")

        else:  # create case
            if self.document is None and self.section is None:
                raise ValueError("Either Document or Section should be set")

            # section has a priority. if section is set, the document of the new
            # section will be taken from the parent section, not from the
            # current 'document' attribute
            if self.section is not None:
                self.document = self.section.document

        super(Section, self).save(*args, **kwargs)


class Property(BaseGnodeObject):
    """
    Class represents a metadata "Property". Defines any kind of metadata
    property and may be linked to the Section.
    """

    # odML fields
    name = models.CharField('name', max_length=100)
    definition = models.CharField(max_length=100, blank=True, null=True)
    mapping = models.CharField(max_length=100, blank=True, null=True)
    dependency = models.CharField(max_length=100, blank=True, null=True)
    dependencyvalue = models.CharField(max_length=100, blank=True, null=True)
    section = VersionedForeignKey(Section)

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return 'property_details', [self.local_id_as_str]


class Value(BaseGnodeObject):
    """
    Class implemented metadata Value.
    """
    type = models.TextField('type')
    uncertainty = models.CharField(max_length=100, blank=True, null=True)
    unit = models.CharField(max_length=100, blank=True, null=True)
    reference = models.CharField(max_length=100, blank=True, null=True)
    definition = models.CharField(max_length=100, blank=True, null=True)
    filename = models.CharField(max_length=100, blank=True, null=True)
    encoder = models.CharField(max_length=100, blank=True, null=True)
    checksum = models.CharField(max_length=100, blank=True, null=True)
    property = VersionedForeignKey(Property)

    def __unicode__(self):
        return self.type

    @models.permalink
    def get_absolute_url(self):
        return 'value_details', [self.local_id_as_str]