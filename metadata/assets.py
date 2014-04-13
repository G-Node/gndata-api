from django.contrib.auth.models import User
from gndata_api.assets import BaseAssets
from metadata.models import Reporter, Article

class Assets(BaseAssets):
    """
    Creates test assets.
    """
    objects = {}
    attr_values = {1: 'one', 2: 'two', 3: 'three', 4: 'four'}

    def __init__(self):
        self.models = [Reporter, Article]

    def fill(self):
        # collector for created objects
        assets = {"reporter": [], "article": []}

        bob = User.objects.get(pk=1)
        ed = User.objects.get(pk=2)

        for i in range(4):
            params = {
                'first_name': "mister %d" % i,
                'last_name': 'from village %d' % (i + 5),
                'email': '%d_email@example.com' % i,
                'owner': bob if i < 3 else ed
            }
            assets['reporter'].append(Reporter.objects.create(**params))

        for i in range(4):
            params = {
                'headline': "%d-th article" % i,
                'reporter': assets["reporter"][0] if i < 2 else assets["reporter"][1],
                'owner': bob
            }
            obj = Article.objects.create(**params)
            assets["article"].append(obj)

        return assets