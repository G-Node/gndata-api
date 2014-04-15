from django.contrib.auth.models import User
from gndata_api.baseassets import BaseAssets
from metadata.models import *

import random


class Assets(BaseAssets):
    """
    Creates test assets.



    """

    def __init__(self):
        self.models = [Document, Section, Property, Value]

    def fill(self):
        def assign_dummy_properties(section):
            r = random.randint(1, 9)
            p = Property.objects.create(
                name="prop %d" % r, section=section, owner=section.owner
            )
            v = Value.objects.create(
                type="value %d" % r, property=p, owner=section.owner
            )
            assets["property"].append(p)
            assets["value"].append(v)

        # collector for created objects
        assets = {"document": [], "section": [], "property": [], "value": []}

        bob = User.objects.get(pk=1)
        ed = User.objects.get(pk=2)

        # documents
        url = "http://portal.g-node.org/odml/terminologies/v1.0/" \
              + "terminologies.xml"
        for i in range(3):
            params = {
                'author': "mister %d" % i,
                'date': timezone.now(),
                'version': 1.0,
                'repository': url,
                'owner': bob if i < 2 else ed
            }
            assets['document'].append(Document.objects.create(**params))

        # sections first level
        for i in range(4):
            params = {
                'name': "%d-th section" % i,
                'type': "level #1",
                'document': assets["document"][0] if i < 2 else assets["document"][2],
                'owner': bob if i < 2 else ed
            }
            obj = Section.objects.create(**params)
            assign_dummy_properties(obj)
            assets["section"].append(obj)

        # sections second level
        for i in range(5):
            sec = assets["section"][0] if i < 2 else assets["section"][1]
            params = {
                'name': "%d-th section" % i,
                'type': "level #2",
                'section': sec,
                'owner': bob
            }
            obj = Section.objects.create(**params)
            assign_dummy_properties(obj)
            assets["section"].append(obj)

        return assets