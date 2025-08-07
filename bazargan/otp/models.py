from django.db import models

from random import randrange
from typing import Any, Dict, Optional, TypedDict, Union

from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

# a user-defined abstract model that includes `uuid`, `created` and `last_updated`
# to track the state of a model. UUID is the primary key of the model.
from common.models import TrackObjectStateMixin


User = get_user_model()


class CompleteOTPType(TypedDict):
    instance: "AuthOTP"
    code: int


class CreateUserAuthOTPType(TypedDict):
    user_auth_otp: "UserAuthOTP"
    complete_otp: CompleteOTPType


class AuthOTP(TrackObjectStateMixin):
    # Number of seconds till the OTP expires
    TIMEOUT = 2 * 60
    # this length should never go below 4
    OTP_LENGTH = 6

    # this is the actual code sent to the user. it is encrypted
    # and signed and not stored as plain text for security purposes
    code = models.CharField(max_length=128)
    # we use a duration field to store the number of seconds
    # the OTP expires from the time of creation, `created`.
    timeout = models.DurationField(default=timezone.timedelta(seconds=TIMEOUT))

    def __str__(self):
        return f"AuthOTP instance at time: {self.created}"

    @classmethod
    def generate_otp(cls, **extra_fields) -> CompleteOTPType:
        """
        The idea behind the generation of an otp or anything secret is simple.
        First, we generate a random code: the otp itself.
        This value is only visible to the user and cannot be inspected in
        any way. To ensure that this process is reversible for verifying
        OTPs, we do this:
        - Use the uuid of the AuthOTP instance as a salt to guarantee
            randomness
        - Sign the generated code and strip the code out of the output
        - Then we store the result from above as the `instance.code`.
        """
        otp: cls = cls(**extra_fields)
        # we know this will always be the length `cls.OTP_LENGTH` digits
        # so we can slice this out after signing
        code = randrange(
            10 ** (cls.OTP_LENGTH - 1), (10 ** cls.OTP_LENGTH) - 1
        )
        # you can swap this for any encryption format you want. I want to
        # stick to core Django
        signed_code = signing.TimestampSigner(salt=str(otp.uuid)).sign(code)

        # we strip out the characters of the length `cls.OTP_LENGTH`
        # this is only because the sigining algorithm from above
        # adds the original code generated to the output. Of course we
        # don't want that to be available in plain sight :D
        otp.code = signed_code[cls.OTP_LENGTH:]
        otp.save()
        # this is the only point you can ever access the actual OTP code
        # If the output is not saved in a variable, it is gone forever
        # and ever. and ever. and ever.
        return {"instance": otp, "code": code}

    @classmethod
    def verify_otp(cls, otp_instance: "AuthOTP", code: int) -> bool:
        """
        Verification only requires that user can provide the first
        4 values of `instance.code` which is the OTP sent to the user's mail.
        Without the OTP, it is impossible to verify the OTP even from the
        stored instance. This guarantees security and places it in the
        hands of the user.
        """
        try:
            unsigned_code = int(
                signing.TimestampSigner(salt=(str(otp_instance.uuid))).unsign(
                    f"{code}{otp_instance.code}", max_age=otp_instance.timeout
                )
            )
        except (signing.BadSignature, signing.SignatureExpired, IndexError):
            return False

        return unsigned_code == code

    def has_expired(self) -> bool:
        # we keep this for jobs to have an API accessible to clear
        # expired otps.
        return self.created + self.timeout < timezone.now()


class UserAuthOTP(models.Model):
    """
    An intermediary table to bind users and otps as otps are meant to be
    anonymous. This table handles management of OTPs for various reasons
    throughout the codebase. Want to generate OTPs to confirm an order?
    Simply add it to the `OTPReasons` enum.
    """

    # we expect this table to be used for future OTPs
    # in various respect. All the developer has to do
    # is add a new `Reason` and do as seen fit.
    class OTPReasons(models.TextChoices):
        ACTIVATE_USER = "ACTIVATE_USER", "Activate User"
        FORGOT_PASSWORD = "FORGOT_PASSWORD", "Forgot password"

        # nothing special, the line was simply too long
        FORGOT_PASSWORD_TOKEN = (
            "FORGOT_PASSWORD_TOKEN",
            "Forgot password token",
        )
        # Used when activating a new user and setting their initial password
        ACTIVE_USER_PASSWORD = (
            "ACTIVE_USER_PASSWORD",
            "Activate user password token",
        )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.ForeignKey(AuthOTP, on_delete=models.CASCADE)
    # a way to group OTPs into malleable categories
    reason = models.CharField(
        max_length=64,
        choices=OTPReasons.choices,
        default=OTPReasons.ACTIVATE_USER,
    )

    def __str__(self) -> str:
        return f"{self.user} | {self.reason}"

    class Meta:
        # we add a composite index made up of the User table and the
        # specified reason. This means that only one `UserAuthOTP`
        # instance can exist for a user per reason. Meanwhile, multiple
        # otps may exist with only 0 or 1 valid at any point in time
        # for a particular `reason`.
        constraints = [
            models.UniqueConstraint(
                fields=["reason", "user"], name="unique_reason_for_user"
            )
        ]

    @classmethod
    def create_otp_for_user(
            cls, user: User, reason: OTPReasons
    ) -> CreateUserAuthOTPType:
        """
        This is the expected method to be used to create an OTP
        for a user. It yields both the auth_otp instance and
        the generated code. Again, the generated code will only be
        available here. If it isn't stored in a variable, it is
        lost forever.
        """
        otp = AuthOTP.generate_otp()
        try:
            # if a `UserAuthOTP` instance already exists for the reason,
            # we reuse it.
            user_auth_otp = cls.objects.get(user=user, reason=reason)
        except cls.DoesNotExist:
            # if not, we create one for the reason
            user_auth_otp = UserAuthOTP(user=user, reason=reason)
        user_auth_otp.otp = otp["instance"]
        user_auth_otp.save()
        return {"user_auth_otp": user_auth_otp, "complete_otp": otp}