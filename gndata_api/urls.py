from django.conf.urls import patterns, include, url
from django.views.generic.base import RedirectView
from django.contrib import admin
admin.autodiscover()

from tastypie.api import Api
from metadata.api import *
from ephys.api import *
from account.api import UserResource

# instantiate resources right there
metadata_resources = [DocumentResource(), SectionResource(), PropertyResource(),
                      ValueResource()]

ephys_resources = [BlockResource(), SegmentResource(), EventArrayResource(),
                   EventResource(), EpochArrayResource(), EpochResource(),
                   RCGResource(), RCResource(), UnitResource(),
                   SpikeTrainResource(), ASAResource(), AnalogSignalResource(),
                   IRSAResource(), SpikeResource()]

v1_api = Api(api_name='v1')
for resource in metadata_resources + ephys_resources + [UserResource()]:
    v1_api.register(resource)

if True:  # FIXME add condition only if in test
    from permissions.tests.fake import FakeResource, FakeOwnedResource
    v1_api.register(FakeResource())
    v1_api.register(FakeOwnedResource())


urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'gndata_api.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    # common -------------------------------------------------------------------

    url(r'^$', RedirectView.as_view(url='/account/login/')),
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
