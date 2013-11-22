import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from tastypie.exceptions import ImmediateHttpResponse
from ambition.utils.views import AjaxFormView
from narrative.api import DatumResource
from narrative.models import Datum, NarrativeConfigManager, NarrativeConfig


class LogView(AjaxFormView):
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
        # determine how the data is based on the headers and build the expected post data for a datum
        # we only support json right now
        content_format = request.GET.get('format', 'json')
        if content_format == 'json':
            # Decode the post so we can check the log level
            post_content = json.loads(request.body)

            # Get the minimum log level
            minimum_log_level = NarrativeConfig.objects.get_minimum_log_level()
            log_level = post_content.get('log_level', minimum_log_level)

            # Log level isn't high enough so ignore it
            if log_level < minimum_log_level:
                return self.get_response()
            try:
                response = DatumResource().dispatch_list(request)
                return response
            except ImmediateHttpResponse, e:
                return e.response
        else:
            raise ImmediateHttpResponse(HttpResponse('Format not supported'))
