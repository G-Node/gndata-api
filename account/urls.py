from django.conf.urls import patterns, url

urlpatterns = patterns('',

    url(r'^login/$', 'django.contrib.auth.views.login',
        {'template_name': 'account/login.html'}, name="login"),

    url(r'^logout/$', 'django.contrib.auth.views.logout_then_login',
        {'login_url': '/account/login/'}, name="logout"),

    url(r'^signup/$', 'account.views.signup', name="signup")

)