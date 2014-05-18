from django.conf.urls import patterns, include, url
from django.views.generic.base import RedirectView
from django.contrib import admin
admin.autodiscover()

from tastypie.api import Api
from metadata.api import *
from ephys.api import *
from account.api import UserResource

# API initialization -----------------------------------------------------------

ACCOUNT_RESOURCES = {
    'user': UserResource(),
}

METADATA_RESOURCES = {
    'document': DocumentResource(),
    'section': SectionResource(),
    'property': PropertyResource(),
    'value': ValueResource()
}

EPHYS_RESOURCES = {
    'block': BlockResource(),
    'segment': SegmentResource(),
    'eventarray': EventArrayResource(),
    'event': EventResource(),
    'epocharray': EpochArrayResource(),
    'epoch': EpochResource(),
    'recordingchannelgroup': RCGResource(),
    'recordingchannel': RCResource(),
    'unit': UnitResource(),
    'spiketrain': SpikeTrainResource(),
    'analogsignalarray': ASAResource(),
    'analogsignal': AnalogSignalResource(),
    'irregularlysampledsignal': IRSAResource(),
    'spike': SpikeResource(),
}

# register user resource
v1_user_api = Api(api_name='user')
for resource in ACCOUNT_RESOURCES.values():
    v1_user_api.register(resource)

# register all resources
v1_metadata_api = Api(api_name='metadata')
for resource in METADATA_RESOURCES.values():
    v1_metadata_api.register(resource)

# register all resources
v1_ephys_api = Api(api_name='electrophysiology')
for resource in EPHYS_RESOURCES.values():
    v1_ephys_api.register(resource)


# Normal URLs ------------------------------------------------------------------

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

    url(r'^api/v1/in_bulk/$', 'gndata_api.views.in_bulk', name="in_bulk"),
    url(r'^api/v1/', include(v1_user_api.urls)),
    url(r'^api/v1/', include(v1_metadata_api.urls)),
    url(r'^api/v1/', include(v1_ephys_api.urls)),

    # Browser  -----------------------------------------------------------------

    url(r'^(?P<resource_type>[\w]+)/?$',
        'gndata_api.views.list_view', name="list_view"),
    url(r'^(?P<resource_type>[\w]+)/(?P<id>[\w]+)/?$',
        'gndata_api.views.detail_view', name="detail_view"),
)
