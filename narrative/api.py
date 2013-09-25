from tastypie.resources import ModelResource
from tastypie.authorization import Authorization
from tastypie.authentication import ApiKeyAuthentication

from .models import Datum


class DatumResource(ModelResource):
    class Meta:
        queryset = Datum.objects.all()
        urlconf_namespace = 'narrative'
        resource_name = 'datum'
        authorization = Authorization()
        authentication = ApiKeyAuthentication()
        allowed_methods = ['get', 'post']
        always_return_data = True
