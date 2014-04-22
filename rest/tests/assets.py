from django.contrib.auth.models import User

from gndata_api.baseassets import BaseAssets
from rest.tests.fake import *


class Assets(BaseAssets):
    """
    Creates assets to test Service and Controller.
    """
    objects = {}
    attr_values = {1: 'one', 2: 'two', 3: 'three', 4: 'four'}

    def __init__(self):
        pass
        self.models = [RestFakeModel, RestFakeOwnedModel]

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
            obj = RestFakeModel.objects.create(**params)
            assets["fake"].append(obj)

        for i in range(4):
            params = {
                'safety_level': 3 if i < 2 else 1,
                'test_attr': i + 1,
                'owner': bob
            }
            obj = RestFakeOwnedModel.objects.create(**params)
            assets["owned"].append(obj)

        return assets