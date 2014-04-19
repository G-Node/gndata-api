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