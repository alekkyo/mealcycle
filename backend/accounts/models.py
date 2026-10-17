from datetime import timedelta

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


def normalize_email_address(email: str) -> str:
    """One canonical form for every email: no surrounding spaces, all lowercase."""
    return email.strip().lower()


def add_primary_email(user) -> None:
    """Give a user created outside allauth's signup a verified primary EmailAddress.

    allauth only lets users log in by code with a verified address on record;
    signup creates it, but the manager and the admin bypass signup.
    """
    from allauth.account.models import EmailAddress

    EmailAddress.objects.create(
        user=user, email=user.email, verified=True, primary=True
    )


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        """Create a regular app user. Passwordless unless a password is given."""
        email = normalize_email_address(email or "")
        if not email:
            raise ValueError("Users must have an email address.")
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)  # without a password, save() makes it unusable
        add_primary_email(user)
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
        add_primary_email(user)
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

    def clean(self):
        # Forms call clean() before their uniqueness check, so normalizing here
        # turns a case-variant duplicate into a form error instead of a 500.
        super().clean()
        self.email = normalize_email_address(self.email or "")

    def save(self, *args, **kwargs):
        self.email = normalize_email_address(self.email)
        # Django treats an empty password as usable, so mark it unusable explicitly.
        if not self.password:
            self.set_unusable_password()
        super().save(*args, **kwargs)


TRIAL_LENGTH = timedelta(days=14)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    trial_started_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Profile of {self.user}"

    @property
    def trial_ends_at(self):
        return self.trial_started_at + TRIAL_LENGTH

    @property
    def trial_is_active(self):
        return timezone.now() < self.trial_ends_at
