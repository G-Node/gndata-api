

class BaseController(object):
    """
    An abstract class that implements basic REST API functions like get single
    object, get list of objects, create, update and delete objects.
    """
    def __init__(self, model):
        pass

    def list(self, request):
        pass

    def get(self, request, pk):
        pass

    def create(self, request):
        pass

    def update(self, request):
        pass

    def delete(self, request, pk):
        pass