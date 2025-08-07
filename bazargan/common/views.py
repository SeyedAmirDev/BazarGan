from django.views.generic import FormView

from .mixins import AjaxRequestMixin

class BaseFormView(FormView, AjaxRequestMixin):
    def form_invalid(self, form):
        if self.is_ajax():
            return self.ajax_form_invalid(form)
        return super().form_invalid(form)
