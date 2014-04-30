from tastypie.resources import ModelResource, ALL
from tastypie.authentication import SessionAuthentication
from tastypie.authorization import ReadOnlyAuthorization

from django.contrib.auth.models import User


class UserResource(ModelResource):
    class Meta:
        queryset = User.objects.all()
        detail_uri_name = 'username'
        resource_name = 'user'
        excludes = ['email', 'password', 'is_active', 'is_staff',
                    'is_superuser', 'last_login', 'date_joined']
        filtering = {
            'username': ALL,
            'first_name': ALL,
            'last_name': ALL
        }
        authentication = SessionAuthentication()
        authorization = ReadOnlyAuthorization()