from django.contrib.auth.models import User

from gndata_api.fake import *


class Assets(object):
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
    @staticmethod
    def fake_models():
        return [FakeModel, FakeParentModel, FakeChildModel, parent_fake]

    @staticmethod
    def _get_fake_object(model, i, at_time=None):
        # always return a fresh object from the DB
        qs = model.objects.all()
        if at_time is not None:
            qs = qs.filter(at_time=at_time)
        return qs.get(test_attr=i)

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
        for model in cls.fake_models():
            create_fake_model(model)

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

    @classmethod
    def flush(cls):
        for model in cls.fake_models():
            delete_fake_model(model)
