from django.contrib.auth.models import User

from permissions.models import SingleAccess
from gndata_api.baseassets import BaseAssets
from permissions.tests.fake import FakeModel, FakeOwnedModel


class Assets(BaseAssets):
    """
    Creates assets to test Permissions module.

    fo1 (public)      fo2 (private, shared with Ed)      fo3 (private)
        |                       |                            |
       fm1                     fm2                          fm3

    """
    objects = {}
    attr_values = {1: 'one', 2: 'two', 3: 'three', 4: 'four'}

    def __init__(self):
        self.models = [FakeModel, FakeOwnedModel]

    def fill(self):
        super(Assets, self).fill()

        # collector for created objects
        assets = {"fake": [], "owned": []}

        bob = User.objects.get(pk=1)
        ed = User.objects.get(pk=2)

        for i in range(3):
            params = {
                'safety_level': 1 if i < 1 else 3,
                'test_attr': i + 1,
                'owner': bob
            }
            obj = FakeOwnedModel.objects.create(**params)
            assets["owned"].append(obj)

        for i in range(3):
            params = {
                'test_attr': i + 1,
                'test_str_attr': self.attr_values[i + 1],
                'owner': bob,
                'test_ref': assets['owned'][i]
            }
            obj = FakeModel.objects.create(**params)
            assets["fake"].append(obj)

        params = {
            'object_id': assets['owned'][1].pk,
            'object_type': 'fakeownedmodel',
            'access_for': ed,
            'access_level': 1
        }
        SingleAccess.objects.create(**params)
        return assets