from django.conf import settings
from django.contrib.auth import views as auth_views, login
from django.urls import reverse_lazy
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.views.generic.edit import FormView, BaseFormView
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth import get_user_model
from django.views import View
from django.views.generic.base import ContextMixin, TemplateResponseMixin

from django.contrib.messages.views import SuccessMessageMixin
from django.utils.translation import gettext_lazy as _

from common.mixins import AjaxRequestMixin

from .email import ActivationEmail, PasswordResetEmail
from .forms import AuthenticationForm, RegisterForm, PasswordResetForm, CheckActiveUserForm
from .tokens import activation_token_generator


User = get_user_model()


class CheckActiveUserView(AjaxRequestMixin, BaseFormView):
    form_class = CheckActiveUserForm
    def form_valid(self, form):
        user = form.save()
        if not user.is_user_verified:
            return self.ajax_success_response(data={
                'action': 'get-token',
                'new_user': True,
                'email': user.email,
                'user_id': user.id,
            })
        else:
            return self.ajax_response(data={
                'action': 'get-password'
            })

    def form_invalid(self, form):
        if self.is_ajax():
            return self.ajax_form_invalid(form)
        return super().form_invalid(form)


class RegisterView(SuccessMessageMixin, auth_views.RedirectURLMixin, FormView):
    """
    Display the register form and handle the registration action.
    """
    form_class = RegisterForm
    template_name = "accounts/register.html"
    redirect_authenticated_user = True
    success_url = reverse_lazy('accounts:password_reset')
    success_message = _("We've sent a verification link to your email. Please check your inbox.")

    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if self.redirect_authenticated_user and self.request.user.is_authenticated:
            redirect_to = self.get_success_url()
            if redirect_to == self.request.path:
                raise ValueError(
                    "Redirection loop for authenticated user detected. Check that "
                    "your LOGIN_REDIRECT_URL doesn't point to a login page."
                )
            return HttpResponseRedirect(redirect_to)
        return super().dispatch(request, *args, **kwargs)

    def get_default_redirect_url(self):
        """Return the default redirect URL."""
        if self.next_page:
            return resolve_url(self.next_page)
        else:
            return resolve_url(settings.LOGIN_REDIRECT_URL)

    def form_valid(self, form):
        user = form.save()
        context = {"user": user}
        to = [user.email]
        print("user register: ", user)
        ActivationEmail(self.request, context).send(to)
        login(self.request, user)
        return super().form_valid(form)


class ActivationConfirmView(TemplateResponseMixin, ContextMixin, View):
    """
    Handles the account activation confirmation process.
    """
    token_generator = activation_token_generator
    template_name = "accounts/activation_confirm.html"

    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        """
        Dispatch method checks the validity of UID and token.
        If valid, marks the user as verified.
        """
        # Ensure required parameters are present
        if "uidb64" not in kwargs or "token" not in kwargs:
            raise ImproperlyConfigured(
                "The URL path must contain 'uidb64' and 'token' parameters."
            )
        # Initialize state
        self.validlink = False
        self.user = self.get_user(kwargs["uidb64"])
        # Validate the user and token
        if self.user and not self.user.is_user_verified:
            if self.check_token(self.user, kwargs["token"]):
                self.validlink = True
                self.user.mark_as_verified()
                return super().dispatch(*args, **kwargs)

        # If invalid, render response with invalid link context
        return self.render_to_response(self.get_context_data())

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests by rendering the template with context.
        """
        return self.render_to_response(self.get_context_data())

    def check_token(self, user, token):
        """
        Validates the provided token for the user.
        """
        return self.token_generator.check_token(user, token)

    def get_user(self, uid):
        """
        Fetches the user corresponding to the given UID.
        Returns None if the user does not exist or UID is invalid.
        """
        try:
            uid = urlsafe_base64_decode(uid).decode()
            return User._default_manager.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist, ValidationError):
            return None

    def get_context_data(self, **kwargs):
        """
        Provides context data to the template, including link validity.
        """
        context = super().get_context_data(**kwargs)
        context["validlink"] = self.validlink
        return context


class LoginView(AjaxRequestMixin, auth_views.LoginView):
    form_class = AuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        login(self.request, form.get_user())

        if self.is_ajax():
            return self.ajax_success_response(data={
                'user_id': self.request.user.id,
                'email': self.request.user.email
            }, message='Logged in successfully')
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.is_ajax():
            return self.ajax_form_invalid(form)
        return super().form_invalid(form)


class LogoutView(auth_views.LogoutView):
    pass

# todo: handle Toast when used ajax
class PasswordResetView(AjaxRequestMixin, SuccessMessageMixin, auth_views.RedirectURLMixin, FormView):
    """
    Display the reset password form and handle the reset password action.
    """
    form_class = PasswordResetForm
    template_name = 'accounts/password_reset.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('accounts:password_reset')
    success_message = _("We've sent a reset password link to your email. Please check your inbox.")

    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        if self.redirect_authenticated_user and self.request.user.is_authenticated:
            redirect_to = self.get_success_url()
            if redirect_to == self.request.path:
                raise ValueError(
                    "Redirection loop for authenticated user detected. Check that "
                    "your LOGIN_REDIRECT_URL doesn't point to a login page."
                )
            return HttpResponseRedirect(redirect_to)
        return super().dispatch(request, *args, **kwargs)

    def get_default_redirect_url(self):
        """Return the default redirect URL."""
        if self.next_page:
            return resolve_url(self.next_page)
        else:
            return resolve_url(settings.LOGIN_REDIRECT_URL)

    def form_valid(self, form):
        user = form.user
        context = {"user": user}
        to = [user.email]
        PasswordResetEmail(self.request, context).send(to)
        if self.is_ajax():
            return self.ajax_success_response(message=self.success_message)
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.is_ajax():
            return self.ajax_form_invalid(form)
        return super().form_invalid(form)


class PasswordResetConfirmView(SuccessMessageMixin, auth_views.PasswordResetConfirmView):
    success_url = reverse_lazy("accounts:login")
    template_name = "accounts/password_reset_confirm.html"
    success_message = _("Your password successfully changed.")

# todo: change reset password email template
# todo: think for this
# todo: set Reset password name for in reset password page
class ActivationResendView(View):
    # form_class = ''
    # success_url = reverse('')
    ...
    # email send with post from client
    # backend validate email
    # check user exists with this email and not verified
    # return user with self.user
    # in form_valid get user
    # and send activation with ActivationEmail
    # redirect back to this page with success toast
