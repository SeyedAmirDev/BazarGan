from django.contrib.auth import views as auth_views, login
from django.urls import reverse_lazy
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.views.generic.edit import FormView, BaseFormView
from django.http import HttpResponseRedirect
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth import get_user_model
from django.contrib.messages.views import SuccessMessageMixin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import SetPasswordForm

from common.mixins import AjaxRequestMixin
from otp.models import UserAuthOTP

from .email import PasswordResetOtpEmail, ActivationOtpEmail
from .forms import AuthenticationForm, PasswordResetForm, CheckActiveUserForm, \
    ReceiveOTPForPasswordResetForm, PasswordResetCompleteForm, ReceiveOTPForActivationForm, \
    ActivationCompleteForm
from .tokens import activation_token_generator


User = get_user_model()


class CheckActiveUserView(AjaxRequestMixin, BaseFormView):
    form_class = CheckActiveUserForm
    def form_valid(self, form):
        user = form.save()

        if not user.is_user_verified:
            # Generate OTP valid for 5 minutes (default in AuthOTP)
            user_auth_otp = UserAuthOTP.create_otp_for_user(
                user, UserAuthOTP.OTPReasons.ACTIVATE_USER
            )
            # Send OTP to user's registered email
            ActivationOtpEmail(
                self.request,
                {"otp": user_auth_otp['complete_otp'], "user": user}
            ).send([user.email])

            return self.ajax_success_response(data={
                'action': 'get-token',
                'new_user': True,
                'email': user.email,
                'user_id': user.id,
                'timer': user_auth_otp['complete_otp']['instance'].TIMEOUT
            })
        else:
            return self.ajax_response(data={
                'action': 'get-password'
            })

    def form_invalid(self, form):
        if self.is_ajax():
            return self.ajax_form_invalid(form)
        return super().form_invalid(form)


INTERNAL_ACTIVATION_SESSION_TOKEN = '_activation_token'


class ActivationLinkConfirmView(SuccessMessageMixin, FormView):
    """
    Handles the account activation confirmation process.
    """
    token_generator = activation_token_generator
    post_activate_login = False
    success_url = reverse_lazy("accounts:login")
    activation_url_token = "activation-set-password"
    success_message = _('you registered successfully. please login!')
    template_name = 'accounts/activation_confirm.html'
    form_class = SetPasswordForm

    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        if "uidb64" not in kwargs or "token" not in kwargs:
            raise ImproperlyConfigured(
                "The URL path must contain 'uidb64' and 'token' parameters."
            )

        self.validlink = False
        self.user = self.get_user(kwargs["uidb64"])

        if self.user is not None:
            token = kwargs["token"]
            if token == self.activation_url_token:
                session_token = self.request.session.get(INTERNAL_ACTIVATION_SESSION_TOKEN)
                if not self.user.is_user_verified and \
                        self.token_generator.check_token(self.user, session_token):
                    self.validlink = True
                    return super().dispatch(*args, **kwargs)
            else:
                if self.token_generator.check_token(self.user, token):
                    # Store the token in the session and redirect to the
                    # activation form at a URL without the token. That
                    # avoids the possibility of leaking the token in the
                    # HTTP Referer header.

                    self.request.session[INTERNAL_ACTIVATION_SESSION_TOKEN] = token
                    redirect_url = self.request.path.replace(
                        token, self.activation_url_token
                    )
                    return HttpResponseRedirect(redirect_url)

        # Display the "Password reset unsuccessful" page.
        return self.render_to_response(self.get_context_data())



    def get_user(self, uidb64):
        try:
            # urlsafe_base64_decode() decodes to bytestring
            uid = urlsafe_base64_decode(uidb64).decode()
            pk = User._meta.pk.to_python(uid)
            user = User._default_manager.get(pk=pk)
        except (
            TypeError,
            ValueError,
            OverflowError,
            User.DoesNotExist,
            ValidationError,
        ):
            user = None
        return user

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.user
        return kwargs

    def form_valid(self, form):
        user = form.save()
        if not self.user.is_user_verified:
            user.mark_as_verified()

        del self.request.session[INTERNAL_ACTIVATION_SESSION_TOKEN]
        if self.post_activate_login:
            login(self.request, user)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["validlink"] = self.validlink
        return context


class LoginView(SuccessMessageMixin, AjaxRequestMixin, auth_views.LoginView):
    form_class = AuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
    success_message = _('logged in successfully!')

    def form_valid(self, form):
        login(self.request, form.get_user())

        if self.is_ajax():
            return self.ajax_success_response(data={
                'user_id': self.request.user.id,
                'email': self.request.user.email
            }, message=self.success_message)
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.is_ajax():
            return self.ajax_form_invalid(form)
        return super().form_invalid(form)


class LogoutView(SuccessMessageMixin, auth_views.LogoutView):
    success_message = _('logged out successfully!')


class PasswordResetOtpView(SuccessMessageMixin, AjaxRequestMixin, BaseFormView):
    """
    Handles password reset functionality by sending a one-time password (OTP) via email.

    This view:
        1. Validates the password reset request (email)
        2. Generates a time-sensitive OTP
        3. Sends the OTP to user's registered email
        4. Handles both regular and AJAX responses
    """
    form_class = PasswordResetForm
    success_message = _('otp sent successfully!')

    def form_valid(self, form):
        # Extract user from validated form data
        user = form.user
        # Generate OTP valid for 5 minutes (default in AuthOTP)
        user_auth_otp = UserAuthOTP.create_otp_for_user(
            user, UserAuthOTP.OTPReasons.FORGOT_PASSWORD
        )
        # Send OTP to user's registered email
        PasswordResetOtpEmail(
            self.request,
            {"otp": user_auth_otp['complete_otp'], "user": user}
        ).send([user.email])

        if self.is_ajax():
            return self.ajax_success_response(
                message=self.success_message,
                data={
                    'timer': user_auth_otp['complete_otp']['instance'].TIMEOUT
                }
            )
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.is_ajax():
            return self.ajax_form_invalid(form)
        return super().form_invalid(form)


class ReceiveOTPForPasswordReset(AjaxRequestMixin, BaseFormView):
    form_class = ReceiveOTPForPasswordResetForm

    def form_valid(self, form):
        code = form.save()
        return self.ajax_success_response(data=code)

    def form_invalid(self, form):
        if self.is_ajax():
            return self.ajax_form_invalid(form)
        return super().form_invalid(form)


class PasswordResetOtpCompleteView(AjaxRequestMixin, BaseFormView):
    form_class = PasswordResetCompleteForm

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return self.ajax_success_response(data={
            'email': user.email,
            'user_id': user.id,
        })

    def form_invalid(self, form):
        if self.is_ajax():
            return self.ajax_form_invalid(form)
        return super().form_invalid(form)


class ActivationOtpView(AjaxRequestMixin, BaseFormView):
    form_class = PasswordResetForm
    success_message = _('activation otp successfully sent.')

    def form_valid(self, form):
        # Extract user from validated form data
        user = form.user
        # Generate OTP valid for 5 minutes (default in AuthOTP)
        user_auth_otp = UserAuthOTP.create_otp_for_user(
            user, UserAuthOTP.OTPReasons.ACTIVATE_USER
        )
        # Send OTP to user's registered email
        ActivationOtpEmail(
            self.request,
            {"otp": user_auth_otp['complete_otp'], "user": user}
        ).send([user.email])

        if self.is_ajax():
            return self.ajax_success_response(
                message=self.success_message,
                data={
                    'timer': user_auth_otp['complete_otp']['instance'].TIMEOUT
                }
            )
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.is_ajax():
            return self.ajax_form_invalid(form)
        return super().form_invalid(form)


class ReceiveOTPForActivationView(AjaxRequestMixin, BaseFormView):
    form_class = ReceiveOTPForActivationForm

    def form_valid(self, form):
        code = form.save()
        return self.ajax_success_response(data=code)

    def form_invalid(self, form):
        if self.is_ajax():
            return self.ajax_form_invalid(form)
        return super().form_invalid(form)


class ActivationCompleteView(AjaxRequestMixin, BaseFormView):
    form_class = ActivationCompleteForm

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return self.ajax_success_response(data={
            'email': user.email,
            'user_id': user.id,
        })

    def form_invalid(self, form):
        if self.is_ajax():
            return self.ajax_form_invalid(form)
        return super().form_invalid(form)


class PasswordResetLinkConfirmView(SuccessMessageMixin, auth_views.PasswordResetConfirmView):
    success_url = reverse_lazy("accounts:login")
    template_name = "accounts/password_reset_confirm.html"
    success_message = _("Your password successfully changed.")
