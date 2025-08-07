from django.contrib.auth import forms as auth_forms
from django.core.exceptions import ValidationError
from django.template import loader
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.core.mail import EmailMultiAlternatives
from django.utils.translation import gettext_lazy as _
from django import forms
from django.core.validators import RegexValidator
from django.db import transaction

from otp.models import AuthOTP, UserAuthOTP


User = get_user_model()


class CheckActiveUserForm(forms.Form):
    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
    )

    def save(self):
        """
        Make sure the email belongs to a user.
        If not, create a new user.
        """
        email = self.cleaned_data.get("email")
        user, _ = User.objects.get_or_create(email=email)
        return user


class ReceiveOTPForPasswordResetForm(forms.Form):
    error_messages = {
        'otp_invalid': _("OTP is invalid"),
    }

    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
    )
    otp = forms.CharField(max_length=AuthOTP.OTP_LENGTH, validators=[
        RegexValidator(
            regex='^[0-9]*$',
            message=_('')
        )
    ])

    def __init__(self, *args, **kwargs):
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        verified = False
        email = self.cleaned_data.get("email")
        otp = self.cleaned_data.get("otp")
        try:
            user: User = User.objects.get(email=email)
            self.user = user
            user_auth_otp = UserAuthOTP.objects.get(
                user=user, reason=UserAuthOTP.OTPReasons.FORGOT_PASSWORD
            )
            verified = AuthOTP.verify_otp(user_auth_otp.otp, int(otp))
        except (User.DoesNotExist, UserAuthOTP.DoesNotExist):
            raise ValidationError(
                self.error_messages["otp_invalid"],
                code="otp_invalid",
            )

        if not verified:
            raise ValidationError(
                self.error_messages["otp_invalid"],
                code="otp_invalid",
            )
        return super().clean()

    @transaction.atomic
    def save(self):
        user_auth_otp = UserAuthOTP.create_otp_for_user(
            self.user, UserAuthOTP.OTPReasons.FORGOT_PASSWORD_TOKEN
        )
        UserAuthOTP.objects.get(
            user=self.user,
            reason=UserAuthOTP.OTPReasons.FORGOT_PASSWORD,
        ).delete()
        return {"code": user_auth_otp["complete_otp"]["code"]}


class PasswordResetCompleteForm(forms.Form):
    error_messages = {
        "password_mismatch": _("The two password fields didn’t match."),
        "request_invalid": _("Password reset request invalid"),
    }

    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
    )

    code = forms.CharField(max_length=AuthOTP.OTP_LENGTH, validators=[
        RegexValidator(
            regex='^[0-9]*$',
            message=_('')
        )
    ])

    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=password_validation.password_validators_help_text_html(),
    )

    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
        help_text=_("Enter the same password as before, for verification."),
    )
    
    def __init__(self, *args, **kwargs):
        self.user = None
        super().__init__(*args, **kwargs)

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError(
                self.error_messages["password_mismatch"],
                code="password_mismatch",
            )
        return password2


    def _post_clean(self):
        super()._post_clean()
        # Validate the password after self.instance is updated with form data
        # by super().
        password = self.cleaned_data.get("password2")
        if password:
            try:
                password_validation.validate_password(password, self.user)
            except ValidationError as error:
                self.add_error("password2", error)


    def clean(self):
        verified = False
        email = self.cleaned_data.get("email")
        code = self.cleaned_data.get("code")
        try:
            user: User = User.objects.get(email=email)
            self.user = user
            user_auth_otp = UserAuthOTP.objects.get(
                user=user, reason=UserAuthOTP.OTPReasons.FORGOT_PASSWORD_TOKEN
            )
            verified = AuthOTP.verify_otp(user_auth_otp.otp, int(code))
        except (User.DoesNotExist, UserAuthOTP.DoesNotExist) as e:
            raise ValidationError(
                self.error_messages["request_invalid"],
                code="request_invalid",
            )

        if not verified:
            raise ValidationError(
                self.error_messages["request_invalid"],
                code="request_invalid",
            )

        return super().clean()

    @transaction.atomic
    def save(self):
        user = self.user
        user.set_password(self.cleaned_data['password1'])
        user.save()
        user_auth_otp = UserAuthOTP.objects.get(
            user=user, reason=UserAuthOTP.OTPReasons.FORGOT_PASSWORD_TOKEN
        )
        user_auth_otp.delete()
        return user


class ReceiveOTPForActivationForm(forms.Form):
    error_messages = {
        'otp_invalid': _("OTP is invalid"),
    }

    otp = forms.CharField(max_length=AuthOTP.OTP_LENGTH, validators=[
        RegexValidator(
            regex='^[0-9]*$',
            message=_('')
        )
    ])

    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
    )

    def __init__(self, *args, **kwargs):
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        verified = False
        email = self.cleaned_data.get("email")
        otp = self.cleaned_data.get("otp")
        try:
            user: User = User.objects.get(email=email)
            self.user = user
            user_auth_otp = UserAuthOTP.objects.get(
                user=user, reason=UserAuthOTP.OTPReasons.ACTIVATE_USER
            )
            verified = AuthOTP.verify_otp(user_auth_otp.otp, int(otp))
        except (User.DoesNotExist, UserAuthOTP.DoesNotExist):
            raise ValidationError(
                self.error_messages["otp_invalid"],
                code="otp_invalid",
            )

        if not verified:
            raise ValidationError(
                self.error_messages["otp_invalid"],
                code="otp_invalid",
            )
        return super().clean()

    @transaction.atomic
    def save(self):
        # mark the user as verified
        user = self.user
        user.mark_as_verified()

        user_auth_otp = UserAuthOTP.create_otp_for_user(
            user, UserAuthOTP.OTPReasons.ACTIVE_USER_PASSWORD
        )
        UserAuthOTP.objects.get(
            user=user,
            reason=UserAuthOTP.OTPReasons.ACTIVATE_USER,
        ).delete()

        return {"code": user_auth_otp["complete_otp"]["code"]}


class ActivationCompleteForm(forms.Form):
    error_messages = {
        "password_mismatch": _("The two password fields didn’t match."),
        "request_invalid": _("Password reset request invalid"),
    }

    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
    )

    code = forms.CharField(max_length=AuthOTP.OTP_LENGTH, validators=[
        RegexValidator(
            regex='^[0-9]*$',
            message=_('')
        )
    ])

    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=password_validation.password_validators_help_text_html(),
    )

    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
        help_text=_("Enter the same password as before, for verification."),
    )

    def __init__(self, *args, **kwargs):
        self.user = None
        super().__init__(*args, **kwargs)

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError(
                self.error_messages["password_mismatch"],
                code="password_mismatch",
            )
        return password2

    def _post_clean(self):
        super()._post_clean()
        # Validate the password after self.instance is updated with form data
        # by super().
        password = self.cleaned_data.get("password2")
        if password:
            try:
                password_validation.validate_password(password, self.user)
            except ValidationError as error:
                self.add_error("password2", error)

    def clean(self):
        verified = False
        email = self.cleaned_data.get("email")
        code = self.cleaned_data.get("code")
        try:
            user: User = User.objects.get(email=email)
            self.user = user
            user_auth_otp = UserAuthOTP.objects.get(
                user=user, reason=UserAuthOTP.OTPReasons.ACTIVE_USER_PASSWORD
            )
            verified = AuthOTP.verify_otp(user_auth_otp.otp, int(code))
        except (User.DoesNotExist, UserAuthOTP.DoesNotExist) as e:
            raise ValidationError(
                self.error_messages["request_invalid"],
                code="request_invalid",
            )

        if not verified:
            raise ValidationError(
                self.error_messages["request_invalid"],
                code="request_invalid",
            )

        return super().clean()

    @transaction.atomic
    def save(self):
        user = self.user
        user.set_password(self.cleaned_data['password1'])
        user.save()
        user_auth_otp = UserAuthOTP.objects.get(
            user=user, reason=UserAuthOTP.OTPReasons.ACTIVE_USER_PASSWORD
        )
        user_auth_otp.delete()
        return user


class PasswordResetForm(forms.Form):
    """
    Form for requesting a password reset by entering an email.
    Validates that the provided email belongs to a registered user.
    """
    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )

    def __init__(self, *args, **kwargs):
        self.user = None
        super().__init__(*args, **kwargs)

    def clean_email(self):
        """
        Make sure the email belongs to a user.
        If not, raise an error.
        """
        email = self.cleaned_data.get("email")

        try:
            self.user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError('user with provided email does not exist.')

        return email


class AuthenticationForm(auth_forms.AuthenticationForm):
    def confirm_login_allowed(self, user):
        """
        Controls whether the given User may log in. This is a policy setting,
        independent of end-user authentication. This default behavior is to
        allow login by active users, and reject login by inactive users.

        If the given user cannot log in, this method should raise a
        ``ValidationError``.

        If the given user may log in, this method should return None.
        """
        super(AuthenticationForm, self).confirm_login_allowed(user)

        if not user.is_verified:
            raise ValidationError("user is not verified.")
