from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
)
from django.utils.translation import gettext_lazy as _

from .validators import validate_iranian_phone_number
from .managers import UserManager


class UserType(models.IntegerChoices):
    customer = 1, _('Customer')
    admin = 2, _('Admin')
    superuser = 3, _('Superuser')


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for our app
    """

    email = models.EmailField(max_length=255, unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    type = models.IntegerField(choices=UserType.choices, default=UserType.customer.value)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    objects = UserManager()

    def __str__(self):
        return self.email

    def mark_as_verified(self):
        """
        Marks the user as verified.
        """
        if not self.is_verified:
            self.is_verified = True
            self.save(update_fields=['is_verified'])

    @property
    def is_user_verified(self):
        """
        Checks if the user is verified.
        """
        return self.is_verified


class Profile(models.Model):
    """
    profile model for our app
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile"
    )
    first_name = models.CharField(max_length=250)
    last_name = models.CharField(max_length=250)
    phone_number = models.CharField(max_length=12, validators=[validate_iranian_phone_number])
    image = models.ImageField(upload_to='profile/', default='profile/default.png')
    # description = models.TextField()

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.email
