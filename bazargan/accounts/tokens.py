from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.conf import settings
from django.utils.crypto import constant_time_compare
from django.utils.http import base36_to_int


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    def check_token(self, user, token):
        if not (user and token):
            return False
        # Parse the token
        try:
            ts_b36, _ = token.split("-")
        except ValueError:
            return False

        try:
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False

        # Check that the timestamp/uid has not been tampered with
        for secret in [self.secret, *self.secret_fallbacks]:
            if constant_time_compare(
                self._make_token_with_timestamp(user, ts, secret),
                token,
            ):
                break
        else:
            return False

        # Check the timestamp is within limit.
        timeout = getattr(settings, "ACTIVATION_ACCOUNT_TIMEOUT", 24 * 60 * 60)
        if (self._num_seconds(self._now()) - ts) > timeout:
            return False

        return True

    def _make_hash_value(self, user, timestamp):
        email_field = user.get_email_field_name()
        email = getattr(user, email_field, "") or ""
        return f"{user.pk}{timestamp}{email}{user.is_user_verified}"

activation_token_generator = AccountActivationTokenGenerator()
