from django.conf.urls import patterns, include, url
from django.views.generic.base import RedirectView, TemplateView
from django.contrib import admin
admin.autodiscover()

from tastypie.api import Api
from metadata.api import *
from account.api import UserResource

v1_api = Api(api_name='v1')
v1_api.register(DocumentResource())
v1_api.register(SectionResource())
v1_api.register(PropertyResource())
v1_api.register(ValueResource())
v1_api.register(UserResource())


urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'gndata_api.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    # common -------------------------------------------------------------------

    url(r'^$', RedirectView.as_view(url='/account/login')),
    #url(r'^home/$', TemplateView.as_view(template_name='home.html')),
    url(r'^home/$', RedirectView.as_view(url='/document/')),
    url(r'^account/', include('account.urls')),
    url(r'^admin/', include(admin.site.urls)),

    # REST API -----------------------------------------------------------------

    url(r'^api/', include(v1_api.urls)),

    # Browser  -----------------------------------------------------------------

    url(r'^(?P<resource_type>[\w]+)/?$',
        'gndata_api.views.list_view', name="list_view"),
    url(r'^(?P<resource_type>[\w]+)/(?P<id>[\w]+)/?$',
        'gndata_api.views.detail_view', name="detail_view"),
)
