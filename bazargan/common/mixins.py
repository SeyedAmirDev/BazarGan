from django.http import JsonResponse
from django import forms


class AjaxRequestMixin:
    def is_ajax(self) -> bool:
        return self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def ajax_response(
            self,
            data: dict,
            status: int = 200,
            message: str = None
    ) -> JsonResponse:
        response_data = {
            'status': 'success' if 200 <= status < 300 else 'error',
            'data': data
        }
        if message:
            response_data['message'] = message
        return JsonResponse(response_data, status=status)

    def _get_form_errors(self, form: forms.Form) -> dict:
        errors = {
            field: [str(error) for error in error_list]
            for field, error_list in form.errors.items()
        }
        if form.non_field_errors():
            errors['non_field_errors'] = [
                str(error) for error in form.non_field_errors()
            ]
        return errors

    def ajax_form_invalid(self, form: forms.Form) -> JsonResponse:
        return self.ajax_response(
            data={'errors': self._get_form_errors(form)},
            status=400,
            message='لطفا خطاهای فرم را اصلاح کنید'
        )

    def ajax_success_response(self, data=None, message=None) -> JsonResponse:
        return self.ajax_response(data or {}, message=message)

    def ajax_error_response(self, message, data=None, status=400) -> JsonResponse:
        return self.ajax_response(data or {}, status=status, message=message)
