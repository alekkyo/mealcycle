import pytest

from accounts.models import User

pytestmark = pytest.mark.django_db


def test_user_changelist_loads(admin_client):
    response = admin_client.get("/admin/accounts/user/")
    assert response.status_code == 200


def test_user_change_form_has_no_password_field(admin_client, admin_user):
    response = admin_client.get(f"/admin/accounts/user/{admin_user.pk}/change/")
    assert response.status_code == 200
    assert b'name="password"' not in response.content


def test_admin_add_user_creates_passwordless_user(admin_client):
    response = admin_client.post(
        "/admin/accounts/user/add/",
        {"email": "New@Example.com", "is_active": "on"},
    )
    assert response.status_code == 302
    user = User.objects.get(email="new@example.com")
    assert user.has_usable_password() is False


def test_admin_login_accepts_uppercase_email(client):
    User.objects.create_superuser(email="boss@example.com", password="s3cret-pass!")
    logged_in = client.login(username="BOSS@example.com", password="s3cret-pass!")
    assert logged_in is True
