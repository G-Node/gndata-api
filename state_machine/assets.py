from state_machine.fake import FakeModel, FakeParentModel, FakeChildModel
from django.contrib.auth.models import User


class Assets(object):

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

    @staticmethod
    def fill():
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

    @staticmethod
    def flush():
        FakeModel.objects.all().delete()
        FakeChildModel.objects.all().delete()
        FakeParentModel.objects.all().delete()