from django.contrib.auth.models import User

from gndata_api.assets import BaseAssets
from gndata_api.fake import *


class Assets(BaseAssets):
    """
    Creates the following assets.

    FakeChild (FK) FakeParent (M2M) Fake
    ---------  ->  ----------  <->  ----

       fc1 ----                ---- fm1
               \              /
       fc2 --------- fp1 ---------- fm2
                             /
       fc3 --------- fp2 ----       fm3

    """
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

        owner = User.objects.get(pk=1)

        fm1 = FakeModel.objects.create(test_attr=1, owner=owner)
        fm2 = FakeModel.objects.create(test_attr=2, owner=owner)
        fm3 = FakeModel.objects.create(test_attr=3, owner=owner)

        fp1 = FakeParentModel.objects.create(test_attr=1, owner=owner)

        # this is how m2m are created now. TODO fix somehow?
        fp1.m2m.through.objects.create(parent=fp1, fake=fm1)
        fp1.m2m.through.objects.create(parent=fp1, fake=fm2)

        fp2 = FakeParentModel.objects.create(test_attr=2, owner=owner)
        fp2.m2m.through.objects.create(parent=fp2, fake=fm2)

        FakeChildModel.objects.create(test_attr=1, test_ref=fp1, owner=owner)
        FakeChildModel.objects.create(test_attr=2, test_ref=fp1, owner=owner)
        FakeChildModel.objects.create(test_attr=3, test_ref=fp2, owner=owner)