import pytest
from django.db import IntegrityError

from accounts.models import User

pytestmark = pytest.mark.django_db


def test_create_user_normalizes_email():
    user = User.objects.create_user(email="  Alex@Example.COM ")
    assert user.email == "alex@example.com"


def test_create_user_has_no_usable_password():
    user = User.objects.create_user(email="alex@example.com")
    assert user.has_usable_password() is False


def test_create_user_defaults():
    user = User.objects.create_user(email="alex@example.com")
    assert user.is_active is True
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.date_joined is not None


def test_create_user_rejects_empty_email():
    with pytest.raises(ValueError):
        User.objects.create_user(email="")


def test_create_user_rejects_blank_email():
    with pytest.raises(ValueError):
        User.objects.create_user(email="   ")


def test_duplicate_email_is_rejected_regardless_of_case():
    User.objects.create_user(email="alex@example.com")
    with pytest.raises(IntegrityError):
        User.objects.create_user(email="ALEX@example.com")


def test_save_without_password_sets_unusable_password():
    user = User(email="Direct@Example.com")
    user.save()
    user.refresh_from_db()
    assert user.email == "direct@example.com"
    assert user.has_usable_password() is False


def test_create_superuser_has_password_and_flags():
    admin = User.objects.create_superuser(
        email="Admin@Example.com", password="s3cret-pass!"
    )
    assert admin.email == "admin@example.com"
    assert admin.has_usable_password() is True
    assert admin.check_password("s3cret-pass!") is True
    assert admin.is_staff is True
    assert admin.is_superuser is True


def test_get_by_natural_key_is_case_insensitive():
    user = User.objects.create_user(email="alex@example.com")
    assert User.objects.get_by_natural_key(" Alex@Example.com ") == user


def test_str_is_email():
    user = User.objects.create_user(email="alex@example.com")
    assert str(user) == "alex@example.com"


def test_create_user_with_password_hashes_it():
    user = User.objects.create_user(email="alex@example.com", password="hunter22!")
    assert user.password != "hunter22!"
    assert user.check_password("hunter22!") is True
