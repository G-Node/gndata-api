from tastypie import fields
from tastypie.resources import ModelResource

from account.api import UserResource


class BaseGNodeResource(ModelResource):

    owner = fields.ForeignKey(UserResource, 'owner')

    def get_schema(self, request, **kwargs):
        """
        Returns a serialized form of the schema of the resource.

        This method is overloaded as the superclass method uses dummy (empty)
        object together with the 'authorized_read_detail' method to check for
        access to the schema, which fails as the owner for the empty object is
        obviously not set.

        Should return a HttpResponse (200 OK).
        """
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)
        self.log_throttled_access(request)
        return self.create_response(request, self.build_schema())