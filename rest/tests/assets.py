from django.contrib.auth.models import User

from gndata_api.assets import BaseAssets
from gndata_api.fake import *


class Assets(BaseAssets):
    """
    Creates assets to test Service and Controller.
    """
    objects = {}
    attr_values = {1: 'one', 2: 'two', 3: 'three', 4: 'four'}

    def __init__(self):
        pass
        self.models = [FakeModel, FakeParentModel, FakeChildModel, parent_fake, FakeOwnedModel]

    def fill(self):
        super(Assets, self).fill()

        # collector for created objects
        assets = {"fake": [], "parent": [], "child": [], "owned": []}

        bob = User.objects.get(pk=1)
        ed = User.objects.get(pk=2)

        for i in range(4):
            owner = bob if i < 3 else ed
            params = {
                'test_attr': i + 1,
                'test_str_attr': self.attr_values[i + 1],
                'owner': owner
            }
            obj = FakeModel.objects.create(**params)
            assets["fake"].append(obj)

        for i in range(2):
            params = {
                'test_attr': i + 1,
                'owner': bob
            }
            obj = FakeParentModel.objects.create(**params)
            assets["parent"].append(obj)

        for i in range(2):
            params = {
                'parent': assets["parent"][0],
                'fake': assets["fake"][i]
            }
            assets["parent"][i].m2m.through.objects.create(**params)

        fp = assets["parent"][1]
        fp.m2m.through.objects.create(parent=fp, fake=assets["fake"][1])

        for i in range(4):
            test_ref = assets["parent"][0] if i < 2 else assets["parent"][1]
            test_ref = None if owner == ed else test_ref
            params = {
                'test_attr': i + 1,
                'test_ref': test_ref,
                'owner': bob if i < 3 else ed
            }
            obj = FakeChildModel.objects.create(**params)
            assets["child"].append(obj)

        for i in range(4):
            params = {
                'safety_level': 3 if i < 2 else 1,
                'test_attr': i + 1,
                'owner': bob
            }
            obj = FakeOwnedModel.objects.create(**params)
            assets["owned"].append(obj)

        return assets