from tastypie.api import Api
from . import api


narrative_api = Api(api_name='api')
narrative_api.register(api.DatumResource())
