# Email Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Passwordless email login with a 6-digit code via django-allauth headless, JWT tokens for the mobile app, a `Profile` with a 14-day trial for every user, and `GET /api/v1/me/`.

**Architecture:** allauth's headless "app" API (`/_allauth/app/v1/...`) handles signup, login codes, email verification and tokens. Our `accounts` app adds `Profile` (created by a `post_save` signal on `User`), email template overrides, and `MeView` (DRF, authenticated by allauth's `JWTTokenAuthentication`).

**Tech Stack:** Django 5.2, DRF, django-allauth[headless] 65.20.x (pulls in PyJWT), pytest-django.

**Spec:** [docs/accounts/spec.md](spec.md). Decisions: [auth.md](auth.md). Source-verified facts: [allauth-research.md](allauth-research.md).

## Global Constraints

- Branch `feature/email-auth` (already created from `main`; holds the auth docs commits). Never commit to `main`.
- All commands run from `backend/` with `venv/bin/...`.
- Code format: 6 numeric digits, dashed, e.g. `482-913` (`ALLAUTH_USER_CODE_FORMAT = {"numeric": True, "length": 6}`; allauth groups ≤8-char codes into 2 dashed chunks, and the dash is optional when typing).
- Code timeout 600 s, max 3 attempts, for both login codes and email verification.
- JWT: HS256, `JWT_SECRET_KEY` from env, access 900 s, refresh 7,776,000 s (90 days), rotation on.
- `ACCOUNT_PREVENT_ENUMERATION = False`. `"accounts"` listed **before** the allauth apps in `INSTALLED_APPS`.
- Email subject is exactly `Your MealCycle code: <code>`.
- Commit messages end with:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_012zGs6upQQTHmFkBVt2UXNh
  ```
- Each task adds its new concepts to `docs/learning/python-for-laravel-devs.md`.

## Source-verified facts (allauth 65.20.0, read from the source before planning)

- `ALLAUTH_USER_CODE_FORMAT` (a `UserCodeFormat` dict: `numeric`, `length`, `dashed`) is the default for all code types. `compare_user_code` strips punctuation and whitespace, so `482913`, `482-913` and `482 913` all match.
- Unknown email on `code/request` with `PREVENT_ENUMERATION=False` → `validation_error("unknown_email")` → 400.
- Login code email template: `account/email/login_code_{subject,message}.txt`, context `code`.
- Signup verification email: `account/email/email_confirmation_signup_{subject,message}.txt`, context `code` (when verification is by code).
- HS256: `HEADLESS_JWT_PRIVATE_KEY` is used as the shared secret.
- Pending flows (between request and confirm) use the session token sent as `X-Session-Token`. Authenticated responses carry `access_token`/`refresh_token`. Refresh: `POST tokens/refresh {"refresh_token"}` → `{"data": {"access_token", "refresh_token"}}`.
- `django.contrib.sites` is not required (`get_current_site` falls back to the request).

## Review Focus

1. **Typing the code without the dash, or with a space** (`482913`, `482 913`): it must be accepted (Task 3 `test_login_code_accepted_without_dash`).
2. **Email in a different case on the second login** (`Alex@Example.com` after signing up as `alex@example.com`): must log into the same account, not fail or create a duplicate (Task 4 `test_login_with_different_case_email_hits_same_account`).
3. **Signing up twice with the same email**: there must still be exactly one User and one Profile (Task 4 `test_returning_user_does_not_duplicate_profile`).
4. **A user created in the admin or with `createsuperuser`** must have exactly one Profile, so `/me` never crashes and the admin "add user" form doesn't 500 (Task 2 tests, incl. `test_admin_add_user_creates_exactly_one_profile`).
5. **An old refresh token reused after rotation** must be rejected (Task 4 `test_refresh_rotates_and_old_token_is_rejected`).

---

### Task 1: Install allauth, configure headless, smoke-test the endpoints

Deliverable: allauth is installed and configured, `/_allauth/app/v1/config` responds, and an unknown-email code request returns 400. A test prints the real response shapes for the later tasks.

**Files:**
- Modify: `backend/requirements.txt`, `backend/config/settings.py`, `backend/config/urls.py`, `backend/.env` (local only), `backend/.env.example`, `.github/workflows/backend.yml`
- Create: `backend/accounts/tests/test_auth_smoke.py`, `backend/accounts/tests/helpers.py`

**Interfaces:**
- Produces: `accounts.tests.helpers.APP` = `"/_allauth/app/v1"`; `extract_code(message) -> str` (pulls the `ddd-ddd` code from an email subject).

- [ ] **Step 1: Install and pin**

```bash
cd ~/Sites/mealcycle/backend
venv/bin/pip install "django-allauth[headless]==65.20.0"
venv/bin/pip freeze | grep -iE '^(django-allauth|pyjwt)=='
```
Add the line `django-allauth[headless]==65.20.0` to `requirements.txt`. PyJWT is a dependency of allauth, so don't list it.

- [ ] **Step 2: Add `JWT_SECRET_KEY` to `.env` and `.env.example`, and to CI**

```bash
KEY=$(venv/bin/python -c "import secrets; print(secrets.token_urlsafe(50))")
printf "JWT_SECRET_KEY='%s'\n" "$KEY" >> .env; unset KEY
```
`.env.example`: add `JWT_SECRET_KEY='change-me'` under `SECRET_KEY`.
`.github/workflows/backend.yml` `env:` add `JWT_SECRET_KEY: ci-only-not-a-real-jwt-secret`.

- [ ] **Step 3: Write the failing smoke test**

`backend/accounts/tests/helpers.py`:
```python
import re

APP = "/_allauth/app/v1"
CODE_RE = re.compile(r"\b(\d{3}-\d{3})\b")


def extract_code(message) -> str:
    """Return the 6-digit code (as 'ddd-ddd') from an email's subject."""
    match = CODE_RE.search(message.subject)
    assert match, f"no code in subject: {message.subject!r}"
    return match.group(1)
```

`backend/accounts/tests/test_auth_smoke.py`:
```python
import pytest

from accounts.tests.helpers import APP

pytestmark = pytest.mark.django_db


def test_config_endpoint_responds(api_client):
    response = api_client.get(f"{APP}/config")
    assert response.status_code == 200
    assert response.json()["data"]["account"]["login_by_code_enabled"] is True


def test_code_request_for_unknown_email_returns_400(api_client):
    response = api_client.post(
        f"{APP}/auth/code/request", {"email": "nobody@example.com"}, format="json"
    )
    assert response.status_code == 400


def test_signup_response_shape(api_client):
    response = api_client.post(f"{APP}/auth/signup", {"email": "new@example.com"}, format="json")
    print("SIGNUP", response.status_code, response.json())  # pins shapes for later tasks
    assert response.status_code == 401  # pending: verify_email flow
    assert "session_token" in response.json()["meta"]
```
Run: `venv/bin/pytest accounts/tests/test_auth_smoke.py -v`
Expected: FAIL with 404 (no allauth URLs yet).

- [ ] **Step 4: Configure allauth in `config/settings.py`**

`INSTALLED_APPS`, after `"rest_framework"`:
```python
    "rest_framework",
    "accounts",  # before allauth so our email templates override allauth's
    "allauth",
    "allauth.account",
    "allauth.headless",
    "core",
```
(Move the existing `"accounts"` line so it isn't listed twice.)

`MIDDLEWARE`: append `"allauth.account.middleware.AccountMiddleware",`.

After `AUTH_USER_MODEL`:
```python
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",  # Django admin login
    "allauth.account.auth_backends.AuthenticationBackend",
]
```

At the end of the file:
```python
# django-allauth: passwordless email login by code (see docs/accounts/spec.md)
ALLAUTH_USER_CODE_FORMAT = {"numeric": True, "length": 6}  # e.g. 482-913

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*"]  # no password → unusable password
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_PREVENT_ENUMERATION = False  # one email screen for signup and login
ACCOUNT_EMAIL_SUBJECT_PREFIX = ""

ACCOUNT_LOGIN_BY_CODE_ENABLED = True
ACCOUNT_LOGIN_BY_CODE_TIMEOUT = 600
ACCOUNT_LOGIN_BY_CODE_MAX_ATTEMPTS = 3

ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED = True
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_TIMEOUT = 600
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_MAX_ATTEMPTS = 3

HEADLESS_ONLY = True
HEADLESS_CLIENTS = ("app",)
HEADLESS_TOKEN_STRATEGY = "allauth.headless.tokens.strategies.jwt.JWTTokenStrategy"
HEADLESS_JWT_ALGORITHM = "HS256"
HEADLESS_JWT_PRIVATE_KEY = env_required("JWT_SECRET_KEY")
HEADLESS_JWT_ACCESS_TOKEN_EXPIRES_IN = 15 * 60
HEADLESS_JWT_REFRESH_TOKEN_EXPIRES_IN = 90 * 24 * 60 * 60
HEADLESS_JWT_ROTATE_REFRESH_TOKEN = True
```

- [ ] **Step 5: Mount the URLs**

`config/urls.py`:
```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("_allauth/", include("allauth.headless.urls")),
    path("api/v1/", include("core.urls")),
]
```

- [ ] **Step 6: Migrate and run the smoke tests**

```bash
venv/bin/python manage.py migrate
venv/bin/pytest accounts/tests/test_auth_smoke.py -v -s
```
Expected: 3 passed. `migrate` creates `account_emailaddress` and `account_emailconfirmation`. **Read the printed `SIGNUP` body** and confirm `meta.session_token` exists. If the shape differs from the facts above, record a ruling and adjust the helpers in Tasks 3–4 to match.

- [ ] **Step 7: Full checks, learning notes, commit**

```bash
venv/bin/pytest -q && venv/bin/python manage.py makemigrations --check --dry-run && venv/bin/ruff format . && venv/bin/ruff check .
```
Learning notes: third-party apps (`INSTALLED_APPS` order and template overrides), `AUTHENTICATION_BACKENDS` (≈ Laravel guards/providers), what "headless" means, and what `/_allauth/app/v1/config` reveals.
```bash
cd ~/Sites/mealcycle && git add .github backend docs/learning && git commit -m "feat(accounts): install and configure django-allauth headless

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012zGs6upQQTHmFkBVt2UXNh"
```

---

### Task 2: `Profile` with the 14-day trial, created for every user

Deliverable: every new User automatically gets a `Profile`. The trial properties work, and the admin shows the profile inline.

**Files:**
- Modify: `backend/accounts/models.py`, `backend/accounts/apps.py`, `backend/accounts/admin.py`
- Create: `backend/accounts/signals.py`, `backend/accounts/migrations/0002_profile.py` (generated), `backend/accounts/tests/test_profile.py`

**Interfaces:**
- Produces: `accounts.models.Profile` (`user` OneToOne `related_name="profile"`, `trial_started_at`, properties `trial_ends_at -> datetime` and `trial_is_active -> bool`); `accounts.models.TRIAL_LENGTH = timedelta(days=14)`.

- [ ] **Step 1: Write the failing tests**

`backend/accounts/tests/test_profile.py`:
```python
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
    admin = User.objects.create_superuser(email="boss@example.com", password="s3cret-pass!")
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
```
Run: `venv/bin/pytest accounts/tests/test_profile.py -v`
Expected: collection error `cannot import name 'TRIAL_LENGTH'`.

- [ ] **Step 2: Add the model**

Append to `backend/accounts/models.py` (add `from datetime import timedelta` at the top, with the other imports):
```python
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
```

- [ ] **Step 3: Add the signal and connect it**

`backend/accounts/signals.py`:
```python
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import Profile, User


@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    """Every user gets a profile (and so a trial) the moment they're created."""
    if created:
        Profile.objects.create(user=instance)
```

`backend/accounts/apps.py`:
```python
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        from accounts import signals  # noqa: F401  (importing connects the receivers)
```

- [ ] **Step 4: Admin inline**

In `backend/accounts/admin.py`, import `Profile` alongside `User`, add above `UserAdmin`:
```python
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    fields = ("trial_started_at",)
```
and inside `UserAdmin` add:
```python
    inlines = (ProfileInline,)

    def get_inlines(self, request, obj):
        # Only on the edit page. On "add user" the post_save signal creates the
        # profile, and an inline would try to create a second one (IntegrityError).
        return self.inlines if obj else ()
```

- [ ] **Step 5: Migration, then tests**

```bash
venv/bin/python manage.py makemigrations accounts --name profile
venv/bin/pytest accounts -v 2>&1 | tail -5
```
Expected: `accounts/migrations/0002_profile.py`; all accounts tests pass.

- [ ] **Step 6: Backfill existing users, migrate**

The superuser you already created has no profile, because the signal didn't exist yet. Add a data migration:
```bash
venv/bin/python manage.py makemigrations accounts --empty --name backfill_profiles
```
Edit the generated `0003_backfill_profiles.py`:
```python
from django.db import migrations


def create_missing_profiles(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Profile = apps.get_model("accounts", "Profile")
    for user in User.objects.filter(profile__isnull=True):
        Profile.objects.create(user=user, trial_started_at=user.date_joined)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_profile")]
    operations = [migrations.RunPython(create_missing_profiles, migrations.RunPython.noop)]
```
```bash
venv/bin/python manage.py migrate
psql -h localhost -U postgres -d mealcycle -Atc "select count(*) from accounts_user u left join accounts_profile p on p.user_id=u.id where p.id is null"
```
Expected: `0` (every user has a profile).

- [ ] **Step 7: Full checks, learning notes, commit**

```bash
venv/bin/pytest -q && venv/bin/python manage.py makemigrations --check --dry-run && venv/bin/ruff format . && venv/bin/ruff check .
```
Learning notes: signals (≈ Eloquent model events/observers), `@receiver`, `AppConfig.ready()`, `OneToOneField`/`related_name` (≈ `hasOne`), `@property` (≈ accessors), data migrations with `RunPython` and why they use `apps.get_model`, admin inlines.
```bash
cd ~/Sites/mealcycle && git add backend/accounts docs/learning && git commit -m "feat(accounts): add Profile with 14-day trial for every user

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012zGs6upQQTHmFkBVt2UXNh"
```

---

### Task 3: Code emails (subject `Your MealCycle code: 482-913`)

Deliverable: both code emails have our subject and a minimal body. Codes are 6 digits and accepted with or without the dash.

**Files:**
- Create: `backend/accounts/templates/account/email/login_code_subject.txt`, `login_code_message.txt`, `email_confirmation_signup_subject.txt`, `email_confirmation_signup_message.txt`, `backend/accounts/tests/test_code_emails.py`

**Interfaces:**
- Consumes: `APP`, `extract_code` (Task 1).

- [ ] **Step 1: Write the failing tests**

`backend/accounts/tests/test_code_emails.py`:
```python
import re

import pytest
from django.core import mail

from accounts.models import User
from accounts.tests.helpers import APP, extract_code

pytestmark = pytest.mark.django_db

SUBJECT_RE = re.compile(r"^Your MealCycle code: \d{3}-\d{3}$")


def _verified_user(email="alex@example.com"):
    from allauth.account.models import EmailAddress

    user = User.objects.create_user(email=email)
    EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
    return user


def test_signup_email_subject_and_body(api_client):
    api_client.post(f"{APP}/auth/signup", {"email": "new@example.com"}, format="json")
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert SUBJECT_RE.match(message.subject), message.subject
    code = extract_code(message)
    assert code in message.body
    assert "10 minutes" in message.body


def test_login_code_email_subject_and_body(api_client):
    _verified_user()
    api_client.post(f"{APP}/auth/code/request", {"email": "alex@example.com"}, format="json")
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert SUBJECT_RE.match(message.subject), message.subject
    assert extract_code(message) in message.body


def test_login_code_accepted_without_dash(api_client):
    _verified_user()
    response = api_client.post(
        f"{APP}/auth/code/request", {"email": "alex@example.com"}, format="json"
    )
    session_token = response.json()["meta"]["session_token"]
    code = extract_code(mail.outbox[0]).replace("-", "")
    response = api_client.post(
        f"{APP}/auth/code/confirm",
        {"code": code},
        format="json",
        HTTP_X_SESSION_TOKEN=session_token,
    )
    assert response.status_code == 200, response.json()
```
Run: `venv/bin/pytest accounts/tests/test_code_emails.py -v`
Expected: the subject tests FAIL (allauth's default subject is "Sign-In Code" / "Please Confirm Your Email Address"). The dash test may already pass; that's fine, because it pins allauth's punctuation stripping.

- [ ] **Step 2: Write the templates**

`login_code_subject.txt` and `email_confirmation_signup_subject.txt` (identical):
```
Your MealCycle code: {{ code }}
```
`login_code_message.txt` and `email_confirmation_signup_message.txt` (identical):
```
{{ code }}

Expires in 10 minutes.
```
(No `{% extends %}`, so allauth's "Hello from example.com" wrapper is left out on purpose. Less text.)

- [ ] **Step 3: Run the tests**

`venv/bin/pytest accounts/tests/test_code_emails.py -v`
Expected: 3 passed.

- [ ] **Step 4: Full checks, learning notes, commit**

```bash
venv/bin/pytest -q && venv/bin/ruff format . && venv/bin/ruff check .
```
Learning notes: Django templates (≈ Blade: `{{ }}`, `{% %}`), template override resolution by app order, `mail.outbox` in tests, regex with `re`.
```bash
cd ~/Sites/mealcycle && git add backend/accounts docs/learning && git commit -m "feat(accounts): branded 6-digit code emails

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012zGs6upQQTHmFkBVt2UXNh"
```

---

### Task 4: Full flows, JWT on our API, and `GET /api/v1/me/`

Deliverable: signup and login end to end return tokens, `/me` works with the access token, refresh rotates tokens, and the failure cases behave as the spec says.

**Files:**
- Create: `backend/accounts/serializers.py`, `backend/accounts/views.py`, `backend/accounts/urls.py`, `backend/accounts/tests/test_auth_flows.py`, `backend/accounts/tests/test_me.py`
- Modify: `backend/config/settings.py` (DRF authentication), `backend/config/urls.py`, `backend/accounts/tests/helpers.py`

**Interfaces:**
- Consumes: `Profile` (Task 2), `APP`/`extract_code` (Task 1).
- Produces: `helpers.signup(client, email) -> dict` and `helpers.login(client, email) -> dict`, each returning the final response JSON containing the tokens. URL `/api/v1/me/` (name `me`).

- [ ] **Step 1: Add flow helpers**

Append to `backend/accounts/tests/helpers.py`:
```python
from django.core import mail


def _confirm(client, path, payload, session_token):
    return client.post(path, payload, format="json", HTTP_X_SESSION_TOKEN=session_token)


def signup(client, email: str) -> dict:
    """Sign up with email + emailed code; return the authenticated response JSON."""
    mail.outbox.clear()
    response = client.post(f"{APP}/auth/signup", {"email": email}, format="json")
    session_token = response.json()["meta"]["session_token"]
    code = extract_code(mail.outbox[-1])
    response = _confirm(client, f"{APP}/auth/email/verify", {"key": code}, session_token)
    assert response.status_code == 200, response.json()
    return response.json()


def login(client, email: str) -> dict:
    """Log in with an emailed code; return the authenticated response JSON."""
    mail.outbox.clear()
    response = client.post(f"{APP}/auth/code/request", {"email": email}, format="json")
    session_token = response.json()["meta"]["session_token"]
    code = extract_code(mail.outbox[-1])
    response = _confirm(client, f"{APP}/auth/code/confirm", {"code": code}, session_token)
    assert response.status_code == 200, response.json()
    return response.json()
```

- [ ] **Step 2: Write the failing flow tests**

`backend/accounts/tests/test_auth_flows.py`:
```python
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core import mail
from django.utils import timezone

from accounts.models import Profile, User
from accounts.tests.helpers import APP, extract_code, login, signup

pytestmark = pytest.mark.django_db


def test_signup_returns_tokens_and_creates_one_user_and_profile(api_client):
    body = signup(api_client, "new@example.com")
    assert body["meta"]["access_token"]
    assert body["meta"]["refresh_token"]
    assert User.objects.filter(email="new@example.com").count() == 1
    assert Profile.objects.filter(user__email="new@example.com").count() == 1


def test_returning_user_does_not_duplicate_profile(api_client):
    signup(api_client, "alex@example.com")
    body = login(api_client, "alex@example.com")
    assert body["meta"]["access_token"]
    assert User.objects.count() == 1
    assert Profile.objects.count() == 1


def test_login_with_different_case_email_hits_same_account(api_client):
    signup(api_client, "alex@example.com")
    login(api_client, "Alex@Example.COM")
    assert User.objects.count() == 1


def test_wrong_code_three_times_burns_the_code(api_client):
    signup(api_client, "alex@example.com")
    mail.outbox.clear()
    response = api_client.post(
        f"{APP}/auth/code/request", {"email": "alex@example.com"}, format="json"
    )
    session_token = response.json()["meta"]["session_token"]
    real_code = extract_code(mail.outbox[-1])
    for _ in range(3):
        response = api_client.post(
            f"{APP}/auth/code/confirm",
            {"code": "000-000"},
            format="json",
            HTTP_X_SESSION_TOKEN=session_token,
        )
        assert response.status_code in (400, 409, 410)
    response = api_client.post(
        f"{APP}/auth/code/confirm",
        {"code": real_code},
        format="json",
        HTTP_X_SESSION_TOKEN=session_token,
    )
    assert response.status_code != 200


def test_expired_code_is_rejected(api_client):
    signup(api_client, "alex@example.com")
    mail.outbox.clear()
    response = api_client.post(
        f"{APP}/auth/code/request", {"email": "alex@example.com"}, format="json"
    )
    session_token = response.json()["meta"]["session_token"]
    code = extract_code(mail.outbox[-1])
    later = timezone.now() + timedelta(minutes=11)
    with patch("django.utils.timezone.now", return_value=later), patch(
        "time.time", return_value=later.timestamp()
    ):
        response = api_client.post(
            f"{APP}/auth/code/confirm",
            {"code": code},
            format="json",
            HTTP_X_SESSION_TOKEN=session_token,
        )
    assert response.status_code != 200


def test_refresh_rotates_and_old_token_is_rejected(api_client):
    body = signup(api_client, "alex@example.com")
    old_refresh = body["meta"]["refresh_token"]
    response = api_client.post(
        f"{APP}/tokens/refresh", {"refresh_token": old_refresh}, format="json"
    )
    assert response.status_code == 200, response.json()
    new = response.json()["data"]
    assert new["access_token"] and new["refresh_token"] != old_refresh
    response = api_client.post(
        f"{APP}/tokens/refresh", {"refresh_token": old_refresh}, format="json"
    )
    assert response.status_code == 400


def test_code_requests_are_rate_limited(api_client):
    signup(api_client, "alex@example.com")
    statuses = [
        api_client.post(
            f"{APP}/auth/code/request", {"email": "alex@example.com"}, format="json"
        ).status_code
        for _ in range(5)
    ]
    assert 429 in statuses or 400 in statuses[3:]
```
Note for the implementer: allauth's exact status codes for "code burned" and "rate limited" are pinned by running these tests. If allauth returns 400 with a `too_many_login_attempts` error instead of 429, tighten the assertion to the observed behaviour and record a ruling. **The intent:** the burned code never logs in, and the 4th rapid request is refused.

`backend/accounts/tests/test_me.py`:
```python
import pytest

from accounts.tests.helpers import signup

pytestmark = pytest.mark.django_db

ME = "/api/v1/me/"


def test_me_requires_token(api_client):
    assert api_client.get(ME).status_code == 401


def test_me_rejects_garbage_token(api_client):
    response = api_client.get(ME, HTTP_AUTHORIZATION="Bearer not-a-real-token")
    assert response.status_code == 401


def test_me_returns_email_and_trial(api_client):
    body = signup(api_client, "alex@example.com")
    access = body["meta"]["access_token"]
    response = api_client.get(ME, HTTP_AUTHORIZATION=f"Bearer {access}")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "alex@example.com"
    assert data["trial_active"] is True
    assert data["trial_ends_at"]
```
Run: `venv/bin/pytest accounts/tests/test_auth_flows.py accounts/tests/test_me.py -v`
Expected: the flow tests pass or fail according to allauth's behaviour (they exercise configuration from Task 1). The `/me` tests FAIL with 404. Investigate any flow failure before moving on.

- [ ] **Step 3: DRF authentication**

In `config/settings.py` `REST_FRAMEWORK`:
```python
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "allauth.headless.contrib.rest_framework.authentication.JWTTokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
```

- [ ] **Step 4: Serializer, view, URLs**

`backend/accounts/serializers.py`:
```python
from rest_framework import serializers

from accounts.models import User


class MeSerializer(serializers.ModelSerializer):
    trial_ends_at = serializers.DateTimeField(source="profile.trial_ends_at")
    trial_active = serializers.BooleanField(source="profile.trial_is_active")

    class Meta:
        model = User
        fields = ["email", "trial_ends_at", "trial_active"]
```
`backend/accounts/views.py`:
```python
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import MeSerializer


class MeView(APIView):
    """The logged-in user's account and trial status."""

    def get(self, request):
        return Response(MeSerializer(request.user).data)
```
`backend/accounts/urls.py`:
```python
from django.urls import path

from accounts.views import MeView

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
]
```
`config/urls.py`, add under the core include:
```python
    path("api/v1/", include("accounts.urls")),
```

- [ ] **Step 5: Run the tests**

```bash
venv/bin/pytest accounts -v 2>&1 | tail -25
```
Expected: all pass. If `test_me_requires_token` returns 403 instead of 401, set `www_authenticate`-style behaviour by keeping `JWTTokenAuthentication` *first* in the list (DRF uses the first class's `authenticate_header` to decide between 401 and 403). Record a ruling if it's still 403.

- [ ] **Step 6: Full checks, learning notes, commit**

```bash
venv/bin/pytest -q && venv/bin/python manage.py makemigrations --check --dry-run && venv/bin/ruff format . && venv/bin/ruff check .
```
Learning notes: JWT (header.payload.signature, why access tokens are short and refresh tokens rotate), `Authorization: Bearer`, `X-Session-Token` for pending flows, `ModelSerializer` + `source="profile.trial_ends_at"` (≈ API Resource), 401 vs 403 in DRF, `patch` on time.
```bash
cd ~/Sites/mealcycle && git add backend docs/learning && git commit -m "feat(accounts): JWT auth for API and GET /api/v1/me/

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012zGs6upQQTHmFkBVt2UXNh"
```

---

### Task 5: Email delivery (Mailtrap / console), docs, PR

Deliverable: with Mailtrap credentials in `.env`, codes arrive in the Mailtrap inbox; without them, they print in the terminal. Docs updated, PR open, CI green.

**Files:**
- Modify: `backend/config/settings.py`, `backend/.env.example`, `CLAUDE.md`, `docs/accounts/spec.md` (status), `docs/README.md`
- Create: `backend/config/tests/test_email_settings.py`

**Interfaces:**
- Consumes: `env_required`/`env_list` from `config.env`.

- [ ] **Step 1: Write the failing test**

`backend/config/tests/test_email_settings.py`:
```python
from config.settings import email_settings_from_env


def test_console_backend_when_no_email_host():
    settings = email_settings_from_env({})
    assert settings["EMAIL_BACKEND"] == "django.core.mail.backends.console.EmailBackend"


def test_smtp_backend_when_email_host_set():
    settings = email_settings_from_env(
        {
            "EMAIL_HOST": "sandbox.smtp.mailtrap.io",
            "EMAIL_HOST_USER": "u",
            "EMAIL_HOST_PASSWORD": "p",
        }
    )
    assert settings["EMAIL_BACKEND"] == "django.core.mail.backends.smtp.EmailBackend"
    assert settings["EMAIL_HOST"] == "sandbox.smtp.mailtrap.io"
    assert settings["EMAIL_PORT"] == 2525
    assert settings["EMAIL_USE_TLS"] is True
```
Run: `venv/bin/pytest config/tests/test_email_settings.py -v`
Expected: `ImportError: cannot import name 'email_settings_from_env'`.

- [ ] **Step 2: Implement it in `config/settings.py`**

```python
def email_settings_from_env(environ) -> dict:
    """SMTP (e.g. Mailtrap) when EMAIL_HOST is set, otherwise print emails to the console."""
    if not environ.get("EMAIL_HOST"):
        return {"EMAIL_BACKEND": "django.core.mail.backends.console.EmailBackend"}
    return {
        "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "EMAIL_HOST": environ["EMAIL_HOST"],
        "EMAIL_PORT": int(environ.get("EMAIL_PORT", "2525")),
        "EMAIL_HOST_USER": environ.get("EMAIL_HOST_USER", ""),
        "EMAIL_HOST_PASSWORD": environ.get("EMAIL_HOST_PASSWORD", ""),
        "EMAIL_USE_TLS": True,
    }


globals().update(email_settings_from_env(os.environ))
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "MealCycle <no-reply@mealcycle.local>")
```
`.env.example`: add
```
# Email (local: Mailtrap → Email Testing → your inbox → SMTP credentials). Leave empty to print emails in the terminal.
EMAIL_HOST=''
EMAIL_PORT='2525'
EMAIL_HOST_USER=''
EMAIL_HOST_PASSWORD=''
DEFAULT_FROM_EMAIL='MealCycle <no-reply@mealcycle.local>'
```
Run: `venv/bin/pytest config/tests/test_email_settings.py -v`. Expected: 2 passed.

- [ ] **Step 3: Manual end-to-end with the console backend**

```bash
venv/bin/python manage.py runserver 8000 > /tmp/mealcycle-run.log 2>&1 &
curl -s -X POST localhost:8000/_allauth/app/v1/auth/signup -H 'Content-Type: application/json' -d '{"email":"curl-test@example.com"}'
grep -A3 "Subject:" /tmp/mealcycle-run.log
```
Expected: the signup response is a 401 "pending" JSON with `meta.session_token`, and the log shows `Subject: Your MealCycle code: ddd-ddd`. Stop the server afterwards.

- [ ] **Step 4: Docs**

CLAUDE.md "Running the Backend" first-time setup: after `cp .env.example .env`, add the line `# set SECRET_KEY and JWT_SECRET_KEY; optional: Mailtrap SMTP credentials (EMAIL_*)`. Under Backend Stack, change the Auth line to `**Auth**: django-allauth headless — passwordless email code login, JWT for the mobile app`.
`docs/accounts/spec.md` status → `Implemented`; `docs/README.md` Accounts row → `Implemented (email login)`.

- [ ] **Step 5: Commit, push, PR, CI**

```bash
venv/bin/pytest -q && venv/bin/ruff format . && venv/bin/ruff check . && venv/bin/python manage.py makemigrations --check --dry-run
cd ~/Sites/mealcycle && git add backend CLAUDE.md docs && git commit -m "feat(accounts): Mailtrap/console email delivery; docs

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012zGs6upQQTHmFkBVt2UXNh"
git push -u origin feature/email-auth
gh pr create --base main --title "Email login with 6-digit codes (allauth headless), JWT, 14-day trial, /me"
gh pr checks --watch
```
The PR body states what changed, why, how to test (curl flow + Mailtrap), and ends with the Claude Code attribution lines.

- [ ] **Step 6: Manual Mailtrap check (the user runs this)**

The user adds their Mailtrap SMTP credentials to `backend/.env`, runs `runserver`, repeats the Step 3 `curl`, and sees the email in the Mailtrap inbox.
