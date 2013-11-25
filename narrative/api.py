import datetime
from datetime import timedelta
import json

from django.conf import settings

from tastypie.resources import ModelResource
from tastypie.authorization import Authorization
from tastypie.authentication import ApiKeyAuthentication

from .models import Datum, DatumLogLevel


class DatumResource(ModelResource):
    class Meta:
        queryset = Datum.objects.all()
        urlconf_namespace = 'narrative'
        resource_name = 'datum'
        authorization = Authorization()
        authentication = ApiKeyAuthentication()
        allowed_methods = ['get', 'post']
        always_return_data = True

    def build_filters(self, filters=None):
        filters = filters or {}

        orm_filters = super(DatumResource, self).build_filters(filters)

        if 'level' in filters:
            status = ''
            try:
                status = DatumLogLevel.status_by_name(filters['level'].title())
            except:
                pass
            orm_filters['log_level'] = status

        return orm_filters

    def hydrate(self, bundle):
        # Convert log level from string to int
        if type(bundle.data.get('log_level')) in [str, unicode]:
            bundle.data['log_level'] = DatumLogLevel.status_by_name(bundle.data.get('log_level'))

        ttl = settings.DEFAULT_NARRATIVE_DATUM_TTL

        # Override the default ttl if one is provided
        if bundle.data.get('ttl'):
            ttl = timedelta(seconds=bundle.data.get('ttl'))

        bundle.data['datum_note_json'] = json.dumps(bundle.data.get('note', ''))
        bundle.data['expiration_time'] = self.get_utc_now() + ttl

        return bundle

    def get_utc_now(self):
        return datetime.datetime.utcnow()
