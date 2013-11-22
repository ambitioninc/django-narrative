from django.conf.urls import patterns, url, include
from tastypie.api import Api
from . import api
from narrative import views


narrative_api = Api(api_name='api')
narrative_api.register(api.DatumResource())

urlpatterns = patterns(
    '',
    url(r'^log/$', views.LogView.as_view(), name='narrative.log'),
    url(r'^', include(narrative_api.urls, namespace='narrative'))
)
