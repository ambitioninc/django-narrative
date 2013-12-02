from django.conf.urls import patterns, url, include
from django.contrib import admin

admin.autodiscover()


urlpatterns = patterns(
    '',
    url(r'^narrative/', include('narrative.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
