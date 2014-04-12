from gndata_api.fake import *


class BaseAssets(object):

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
    def fill(cls):
        for model in cls.fake_models():
            create_fake_model(model)

    @classmethod
    def flush(cls):
        for model in cls.fake_models():
            delete_fake_model(model)
