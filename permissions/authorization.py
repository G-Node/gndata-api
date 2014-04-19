from tastypie.authorization import Authorization
from tastypie.exceptions import Unauthorized


class ACLManageAuthorization(Authorization):
    """ simple read-only authorization for ACLs. assumes filtering for
    permissions (ACL records of SingleAccess object) for the current user are
    filtered in the resource class.

    Management of ACL records is implemented separately in the resource module.
    """

    def read_list(self, object_list, bundle):
        return object_list

    def read_detail(self, object_list, bundle):
        return True

    def create_list(self, object_list, bundle):
        return []

    def create_detail(self, object_list, bundle):
        return False

    def update_list(self, object_list, bundle):
        return []

    def update_detail(self, object_list, bundle):
        return False

    def delete_list(self, object_list, bundle):
        raise Unauthorized("Sorry, no deletes.")

    def delete_detail(self, object_list, bundle):
        return False


class BaseAuthorization(Authorization):

    def read_list(self, object_list, bundle):
        # this assumes object_list = 'QuerySet' from 'ModelResource'
        model = object_list.model
        if hasattr(model, 'security_filter'):
            return model.security_filter(object_list, bundle.request.user)
        else:
            return object_list.filter(owner=bundle.request.user)

    def read_detail(self, object_list, bundle):
        # Is the requested object owned by the user?
        user = bundle.request.user
        obj = bundle.obj
        if not hasattr(obj, 'is_accessible') or not obj.is_accessible(user):
            raise Unauthorized("You are not authorized to access this object")

        return obj.is_accessible(user)

    def create_list(self, object_list, bundle):
        # Assuming they're auto-assigned to ``user``.
        return object_list

    def create_detail(self, object_list, bundle):
        return bundle.obj.owner == bundle.request.user

    def update_list(self, object_list, bundle):
        return []

    def update_detail(self, object_list, bundle):
        user = bundle.request.user
        obj = bundle.obj
        if not hasattr(obj, 'is_editable') or not obj.is_editable(user):
            raise ReferenceError('You are not authorized to change this object')

        return obj.is_editable(user)

    def delete_list(self, object_list, bundle):
        raise Unauthorized("Sorry, no deletes.")

    def delete_detail(self, object_list, bundle):
        user = bundle.request.user
        obj = bundle.obj
        if not hasattr(obj, 'is_editable') or not obj.is_editable(user):
            raise ReferenceError('You are not authorized to change this object')

        return obj.is_editable(user)