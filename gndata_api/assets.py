from gndata_api.fake import *


class BaseAssets(object):

    models = []

    @staticmethod
    def get_fake_object(model, i, at_time=None):
        # always return a fresh object from the DB
        qs = model.objects.all()
        if at_time is not None:
            qs = qs.filter(at_time=at_time)
        return qs.get(test_attr=i)

    def fill(self):
        for model in self.models:
            create_fake_model(model)

    def flush(self):
        for model in self.models:
            delete_fake_model(model)
