from django.conf.urls import patterns, url

urlpatterns = patterns('',

    url(r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'account/login.html'}),
    url(r'^logout/$', 'django.contrib.auth.views.logout_then_login'),
    url(r'^signup/$', 'account.views.signup')

)