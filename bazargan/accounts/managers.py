from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    def create_user(self, email, password, **extra_fields):
        """
        Create and save a User with the given email and password.
        :param email: string
        :param password: string
        :param extra_fields: additional fields passed
        :return: User
        """

        if not email:
            raise ValueError(_("The email must be set."))

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()

        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a Superuser with the given email and password.
        :param email: string
        :param password: string
        :param extra_fields: additional fields passed
        :return: Superuser
        """
        from .models import UserType

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_verified", True)
        extra_fields.setdefault("type", UserType.superuser.value)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        if extra_fields.get("is_verified") is not True:
            raise ValueError(_("Superuser must have is_verified=True."))
        if extra_fields.get("type") is not UserType.superuser.value:
            raise ValueError(_("Superuser must have superuser type."))


        return self.create_user(email, password, **extra_fields)
