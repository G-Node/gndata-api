from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from gndata_api.utils import update_keys_for_model

from metadata.models import *
from metadata.tests.assets import Assets


class TestSection(TestCase):
    """
    Class tests certain aspects of the Section model.
    """
    fixtures = ["users.json"]

    def setUp(self):
        for model in [Document, Section, Property, Value]:
            update_keys_for_model(model)
        self.assets = Assets().fill()
        self.bob = User.objects.get(pk=1)
        self.ed = User.objects.get(pk=2)

    def test_create_parent_validation(self):
        """ test all create combinations with parent Section & Document. test
        uses queryset.create() method which uses obj.save() so there is no need
        to test obj.save() separately. """

        # both parents are None
        params = {
            'name': "test section",
            'type': "level #1",
            'owner': self.bob
        }
        self.assertRaises(ValidationError, Section.objects.create, **params)

        # section is set, document is None
        params['type'] = "level #2"
        params['section'] = self.assets["section"][0]
        sec = Section.objects.create(**params)
        self.assertEqual(sec.document.pk, self.assets['section'][0].document.pk)

        # both parents are set
        params['document'] = self.assets['document'][0]
        sec = Section.objects.create(**params)
        self.assertEqual(sec.document.pk, self.assets["section"][0].document.pk)

    def test_update_new_section(self):
        """ only section has changed """
        pk = self.assets['section'][0].pk
        qs = Section.objects.filter(pk=pk)
        qs.update(**{'section': self.assets['section'][1]})

        new = Section.objects.get(pk=pk)
        self.assertEqual(new.document.pk, self.assets['section'][1].document.pk)

    def test_update_both_parents_changed(self):
        """ both section and document have changed, give priority to the new
        section, copy document from it """
        pk = self.assets['section'][0].pk
        qs = Section.objects.filter(pk=pk)
        qs.update(**{
            'section': self.assets['section'][1],
            'document': self.assets['document'][1]
        })

        new = Section.objects.get(pk=pk)
        self.assertEqual(new.document.pk, self.assets['section'][1].document.pk)

    def test_update_new_document(self):
        """ only document has changed """
        pk = self.assets['section'][4].pk
        qs = Section.objects.filter(pk=pk)
        params = {'document': self.assets['document'][1]}
        self.assertRaises(ValueError, qs.update, **params)

        pk = self.assets['section'][0].pk
        qs = Section.objects.filter(pk=pk)
        qs.update(**{'document': self.assets['document'][1]})

        new = Section.objects.get(pk=pk)
        self.assertEqual(new.document.pk, self.assets['document'][1].pk)

    def test_delete_cascade(self):
        pk1 = self.assets['section'][0].pk
        pk2 = self.assets['section'][4].pk

        Section.objects.get(pk=pk1).delete()

        self.assertRaises(ObjectDoesNotExist, Section.objects.all().get, pk=pk2)