from django.http import JsonResponse
from django.conf import settings

class AjaxExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            response_data = {
                'status': 'error',
                'message': 'خطای سرور',
                'data': {}
            }
            if settings.DEBUG:
                response_data['debug'] = {
                    'exception': str(exception),
                    'type': exception.__class__.__name__
                }
            return JsonResponse(response_data, status=500)
