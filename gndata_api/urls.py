from django.conf.urls import patterns, include, url
from django.views.generic.base import RedirectView, TemplateView

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'gndata_api.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^$', RedirectView.as_view(url='/account/login')),

    url(r'^home/$', TemplateView.as_view(template_name='home.html')),

    url(r'^account/', include('account.urls')),

    url(r'^admin/', include(admin.site.urls)),
)
