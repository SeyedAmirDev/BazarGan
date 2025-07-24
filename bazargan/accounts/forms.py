from django.contrib.auth import forms as auth_forms
from django.core.exceptions import ValidationError
from django.template import loader
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.core.mail import EmailMultiAlternatives
from django.utils.translation import gettext_lazy as _
from django import forms


User = get_user_model()


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


class RegisterForm(auth_forms.BaseUserCreationForm):
    """
    A form that creates a user, with no privileges, from the given username and
    password.
    """
    class Meta:
        model = User
        fields = ("email",)

    def clean_email(self):
        """Reject email that differ only in case."""
        email = self.cleaned_data.get("email")
        if (
            email
            and self._meta.model.objects.filter(email__iexact=email).exists()
        ):
            self._update_errors(
                ValidationError(
                    {
                        "email": self.instance.unique_error_message(
                            self._meta.model, ["email"]
                        )
                    }
                )
            )
        else:
            return email
