from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


def normalize_email_address(email: str) -> str:
    """One canonical form for every email: no surrounding spaces, all lowercase."""
    return email.strip().lower()


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, **extra_fields):
        """Create a regular, passwordless app user."""
        email = normalize_email_address(email or "")
        if not email:
            raise ValueError("Users must have an email address.")
        user = self.model(email=email, **extra_fields)
        user.save(using=self._db)  # save() gives the user an unusable password
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create an admin who can log into /admin/ with a password."""
        email = normalize_email_address(email or "")
        if not email:
            raise ValueError("Users must have an email address.")
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def get_by_natural_key(self, username):
        """Used by login: match the email whatever its case or spacing."""
        return self.get(email=normalize_email_address(username))


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        self.email = normalize_email_address(self.email)
        # Django treats an empty password as usable, so mark it unusable explicitly.
        if not self.password:
            self.set_unusable_password()
        super().save(*args, **kwargs)
