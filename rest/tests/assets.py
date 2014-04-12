from django.contrib.auth.models import User

from gndata_api.assets import BaseAssets
from gndata_api.fake import *


class Assets(BaseAssets):
    """
    Creates assets to test Service and Controller.
    """
    objects = {}
    attr_values = {1: 'one', 2: 'two', 3: 'three', 4: 'four'}

    @classmethod
    def fm(cls, i, at_time=None):
        return cls._get_fake_object(FakeModel, i, at_time)

    @classmethod
    def fp(cls, i, at_time=None):
        return cls._get_fake_object(FakeParentModel, i, at_time)

    @classmethod
    def fc(cls, i, at_time=None):
        return cls._get_fake_object(FakeChildModel, i, at_time)

    @classmethod
    def fill(cls):
        super(Assets, cls).fill()

        # collector for created objects
        assets = {"fake": [], "parent": [], "child": []}

        bob = User.objects.get(pk=1)
        ed = User.objects.get(pk=2)

        for i in range(4):
            owner = bob if i < 3 else ed
            params = {
                'test_attr': i,
                'test_str_attr': cls.attr_values[i],
                'owner': owner
            }
            obj = FakeModel.objects.create(**params)
            assets["fake"].append(obj)

        for i in range(2):
            params = {
                'test_attr': i,
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
                'test_attr': i,
                'test_ref': test_ref,
                'owner': bob if i < 3 else ed
            }
            obj = FakeChildModel.objects.create(**params)
            assets["child"].append(obj)

        return assets