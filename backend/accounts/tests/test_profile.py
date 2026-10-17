from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import TRIAL_LENGTH, Profile, User

pytestmark = pytest.mark.django_db


def test_trial_length_is_14_days():
    assert TRIAL_LENGTH == timedelta(days=14)


def test_create_user_creates_profile():
    user = User.objects.create_user(email="alex@example.com")
    assert Profile.objects.filter(user=user).count() == 1
    assert user.profile.trial_started_at is not None


def test_create_superuser_creates_profile():
    admin = User.objects.create_superuser(
        email="boss@example.com", password="s3cret-pass!"
    )
    assert admin.profile is not None


def test_saving_existing_user_does_not_create_second_profile():
    user = User.objects.create_user(email="alex@example.com")
    user.is_active = False
    user.save()
    assert Profile.objects.filter(user=user).count() == 1


def test_trial_ends_14_days_after_start():
    user = User.objects.create_user(email="alex@example.com")
    profile = user.profile
    assert profile.trial_ends_at == profile.trial_started_at + timedelta(days=14)


def test_trial_is_active_during_trial():
    user = User.objects.create_user(email="alex@example.com")
    assert user.profile.trial_is_active is True


def test_trial_is_inactive_after_14_days():
    user = User.objects.create_user(email="alex@example.com")
    user.profile.trial_started_at = timezone.now() - timedelta(days=14, seconds=1)
    assert user.profile.trial_is_active is False


def test_admin_add_user_creates_exactly_one_profile(admin_client):
    response = admin_client.post(
        "/admin/accounts/user/add/", {"email": "new@example.com", "is_active": "on"}
    )
    assert response.status_code == 302
    assert Profile.objects.filter(user__email="new@example.com").count() == 1


def test_admin_user_page_shows_profile_inline(admin_client, admin_user):
    response = admin_client.get(f"/admin/accounts/user/{admin_user.pk}/change/")
    assert response.status_code == 200
    assert b"trial_started_at" in response.content
