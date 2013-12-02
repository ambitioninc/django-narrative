import json
from django.http import HttpResponseBadRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from tastypie.exceptions import ImmediateHttpResponse
from narrative.api import DatumResource
from narrative.models import NarrativeConfig, DatumLogLevel


class LogView(View):
    """

    """

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        """
        This method is extended simply to add the csrf_exempt decorator
        """
        return super(LogView, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        """

        @return: A json response
        """
        # Get the minimum log level
        minimum_log_level = NarrativeConfig.objects.get_minimum_log_level()
        log_level = minimum_log_level

        # Determine the data format based on headers and send the correct data to an api for processing
        # NOTE: We only support json right now
        content_type = request.META.get('CONTENT_TYPE', 'application/json')
        if content_type == 'application/json':
            try:
                # Decode the post so we can check the log level
                post_content = json.loads(request.body)
            except Exception:
                return HttpResponseBadRequest('Invalid json')

            # Determine the log level
            if type(post_content) is dict:
                log_level = post_content.get('log_level', minimum_log_level)

            if type(log_level) in [str, unicode]:
                log_level = DatumLogLevel.status_by_name(log_level)
        else:
            return HttpResponseBadRequest('Format not supported')

        # Check if the log level is high enough to store
        if log_level < minimum_log_level:
            # Log level isn't high enough so ignore it
            return HttpResponse(json.dumps({
                'success': True
            }), mimetype='application/json')
        try:
            # Send the data to the api to be logged
            response = DatumResource().dispatch_list(request)
            return response
        except ImmediateHttpResponse, e:
            return e.response
