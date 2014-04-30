from django.conf.urls import patterns, include, url
from django.contrib import admin
admin.autodiscover()

from tastypie.api import Api
from permissions.tests.fake import FakeResource, FakeOwnedResource
from account.api import UserResource

v1_api = Api(api_name='v1')

v1_api.register(FakeResource())
v1_api.register(FakeOwnedResource())
v1_api.register(UserResource())

urlpatterns = patterns('',
    url(r'^api/', include(v1_api.urls)),
)