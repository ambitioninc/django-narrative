from tastypie.resources import ModelResource
from tastypie.authorization import Authorization
from tastypie.authentication import SessionAuthentication, ApiKeyAuthentication, MultiAuthentication

from .models import Event


class EventResource(ModelResource):
    class Meta:
        queryset = Event.objects.all()
        urlconf_namespace = 'narrative'
        resource_name = 'event'
        authorization = Authorization()
        authentication = MultiAuthentication(SessionAuthentication(), ApiKeyAuthentication())
        allowed_methods = ['get', 'post']
        always_return_data = True
