# Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the `startproject` scaffold into a production-ready base: env-driven settings, Postgres, an email-only custom User, DRF, a `/api/v1/health/` endpoint, pytest, ruff and GitHub Actions CI.

**Architecture:** One Django project (`backend/mealcycle/`) with two apps: `accounts` (custom User) and `core` (project-wide features, starting with the health check). Configuration comes only from environment variables, read by small helpers in `mealcycle/env.py`. Tests run with pytest against a throwaway Postgres database.

**Tech Stack:** Python 3.13 (pyenv), Django 5.2 LTS, Django REST Framework, psycopg 3, python-dotenv, dj-database-url, pytest + pytest-django, ruff, GitHub Actions.

**Spec:** [docs/foundation/spec.md](spec.md). Decisions and their reasoning: [docs/foundation/decisions.md](decisions.md)

## Global Constraints

- Python **3.13.x**; Django **5.2.x** (LTS). Do not upgrade to Django 6.
- Postgres driver is `psycopg[binary]` (v3), **not** `psycopg2`.
- All commands run from `backend/` using the venv binaries (`venv/bin/python`, `venv/bin/pip`, `venv/bin/pytest`, `venv/bin/ruff`) unless stated otherwise.
- Local DB: `postgres://postgres@localhost:5432/mealcycle` (DBngin Postgres 17). **Never touch the `kespas` or `kespas_testing` databases.**
- **Do not run `manage.py migrate` against the real database until Task 3 Step 9**, after `AUTH_USER_MODEL` is set.
- No secrets in git: `SECRET_KEY` lives only in `backend/.env` (gitignored) and as a fake placeholder in CI.
- All API routes live under `/api/v1/`.
- Branch: `feature/foundation`, created from `docs/project-context` so the docs ship in the same PR. Never commit to `main`.
- Every commit message ends with:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_012zGs6upQQTHmFkBVt2UXNh
  ```
- The user is learning Python. Each task ends by adding the new concepts it introduced to `docs/learning/python-for-laravel-devs.md`, with Laravel comparisons.

## Review Focus

1. **Email case and whitespace at login.** An admin typing `Alex@Example.com ` should still log in. `get_by_natural_key` normalizes (Task 3 test `test_get_by_natural_key_is_case_insensitive`).
2. **Users created without a password** (admin "add user" form, `User(...).save()`) must get an *unusable* password. Django treats `""` as usable (Task 3 tests `test_save_without_password_sets_unusable_password`, `test_admin_add_user_creates_passwordless_user`).
3. **A whitespace-only email** (`"   "`) must be rejected like an empty one (Task 3 test `test_create_user_rejects_blank_email`).
4. **A missing required env var** should fail with a clear message naming the variable, not a bare `KeyError` (Task 2 test `test_env_required_raises_clear_error_when_missing`).
5. **`ALLOWED_HOSTS` written as `"localhost, 127.0.0.1,"`** (spaces, trailing comma) must parse to clean hostnames (Task 2 test `test_env_list_strips_spaces_and_drops_empties`).

Also: generated `SECRET_KEY`s can contain `$` and `#`, so `.env` values are wrapped in **single quotes**, which python-dotenv reads literally (Task 2 Step 6).

---

### Task 0: Branch

- [ ] **Step 1: Create the implementation branch**

```bash
cd ~/Sites/mealcycle
git checkout docs/project-context
git checkout -b feature/foundation
```
Expected: `Switched to a new branch 'feature/foundation'`

---

### Task 1: Python 3.13 runtime, dependencies, ruff

Deliverable: the venv runs Python 3.13 with all pinned dependencies, and the whole codebase passes `ruff check` and `ruff format --check`.

**Files:**
- Create: `backend/.python-version`, `backend/requirements-dev.txt`, `backend/pyproject.toml`
- Modify: `backend/requirements.txt` (rewritten), `.gitignore`, every existing `.py` file (reformatted by ruff only)
- Delete + recreate: `backend/venv/` (gitignored, so it doesn't show in git)

**Interfaces:**
- Produces: `backend/venv/` on 3.13; `pyproject.toml` with a `[tool.ruff]` section (Task 2 adds `[tool.pytest.ini_options]`).

- [ ] **Step 1: Get the latest Python 3.13 build definitions**

pyenv 2.6.0 only knows about versions up to 3.13.3. Upgrade it so we get the newest 3.13 security release:
```bash
brew upgrade pyenv
pyenv latest --known 3.13
```
Expected: prints a version `3.13.N` with N ≥ 3. (If `brew upgrade` fails, continue with 3.13.3.)

- [ ] **Step 2: Install it and pin it for `backend/`**

```bash
cd ~/Sites/mealcycle/backend
pyenv install --skip-existing "$(pyenv latest --known 3.13)"
pyenv local "$(pyenv latest 3.13)"
cat .python-version
python --version
```
Expected: `.python-version` contains the exact version (e.g. `3.13.9`), and `python --version` prints the same. `pyenv local` writes `.python-version` (≈ `.nvmrc`). pyenv reads it whenever you're inside `backend/`.

- [ ] **Step 3: Rebuild the venv on 3.13**

```bash
rm -rf venv
python -m venv venv
venv/bin/python --version
venv/bin/python -m pip install --upgrade pip
```
Expected: `Python 3.13.N`.

- [ ] **Step 4: Install production dependencies**

```bash
venv/bin/pip install "Django>=5.2,<5.3" djangorestframework "psycopg[binary]" python-dotenv dj-database-url
venv/bin/pip freeze | grep -iE '^(django|djangorestframework|psycopg|python-dotenv|dj-database-url)=='
```
Expected: one line per package with its exact installed version.

- [ ] **Step 5: Write `backend/requirements.txt` with exact pins**

Replace the whole file. Use the versions printed in Step 4 (`X.Y.Z` stands for each one):
```
Django==X.Y.Z
djangorestframework==X.Y.Z
psycopg[binary]==X.Y.Z
python-dotenv==X.Y.Z
dj-database-url==X.Y.Z
```
(`asgiref`, `sqlparse` and `typing_extensions` are dependencies of these packages and are no longer listed. pip resolves them itself. `psycopg2-binary` is removed.)

- [ ] **Step 6: Install dev dependencies and write `backend/requirements-dev.txt`**

```bash
venv/bin/pip install pytest pytest-django ruff
venv/bin/pip freeze | grep -iE '^(pytest|pytest-django|ruff)=='
```
Create `backend/requirements-dev.txt` with those exact versions:
```
-r requirements.txt
pytest==X.Y.Z
pytest-django==X.Y.Z
ruff==X.Y.Z
```
Then confirm a clean install from the files works:
```bash
venv/bin/pip install -r requirements-dev.txt
```
Expected: `Requirement already satisfied` for everything.

- [ ] **Step 7: Create `backend/pyproject.toml` with the ruff config**

```toml
[tool.ruff]
target-version = "py313"
line-length = 88
extend-exclude = ["**/migrations/**"]

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "UP", "DJ"]
# The formatter handles line length. E501 would only flag long strings it can't split.
ignore = ["E501"]
```

- [ ] **Step 8: Add tool caches to `.gitignore`**

Append to the `# Python` block in `/Users/alexkua/Sites/mealcycle/.gitignore`:
```
.pytest_cache/
.ruff_cache/
```

- [ ] **Step 9: Run ruff and auto-fix the scaffold**

```bash
venv/bin/ruff check . --fix
venv/bin/ruff format .
venv/bin/ruff check .
venv/bin/ruff format --check .
```
Expected: the last two print `All checks passed!` and `N files already formatted`. (The formatter switches the scaffold's `'single'` quotes to `"double"`. That's expected.)

- [ ] **Step 10: Check Django still boots**

```bash
venv/bin/python manage.py check
```
Expected: `System check identified no issues (0 silenced).` (The settings still use SQLite at this point. That's fine; Task 2 changes it.)

- [ ] **Step 11: Learning notes**

Add a section to `docs/learning/python-for-laravel-devs.md` covering: what pyenv is (≈ nvm), `.python-version`, `pip freeze` and why we pin `==` versions, `-r` includes in requirements files, `pyproject.toml`, and ruff (≈ ESLint + Prettier).

- [ ] **Step 12: Commit**

```bash
cd ~/Sites/mealcycle
git add .gitignore backend/.python-version backend/requirements.txt backend/requirements-dev.txt backend/pyproject.toml backend/manage.py backend/mealcycle docs/learning
git commit -m "chore(backend): upgrade to Python 3.13, pin deps, add ruff

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012zGs6upQQTHmFkBVt2UXNh"
```

---

### Task 2: Env-driven settings and Postgres

Deliverable: settings read only from the environment, Django connects to the `mealcycle` Postgres database, and pytest runs.

**Files:**
- Create: `backend/mealcycle/env.py`, `backend/mealcycle/tests/__init__.py`, `backend/mealcycle/tests/test_env.py`, `backend/mealcycle/tests/test_database.py`, `backend/conftest.py`, `backend/.env` (gitignored, not committed)
- Modify: `backend/mealcycle/settings.py`, `backend/.env.example`, `backend/pyproject.toml`

**Interfaces:**
- Produces: `mealcycle.env.env_required(name: str) -> str` (raises `django.core.exceptions.ImproperlyConfigured`) and `mealcycle.env.env_list(name: str) -> list[str]`. Module-level `DEBUG: bool` in settings (Task 4 uses it in `REST_FRAMEWORK`).

- [ ] **Step 1: Add the pytest config**

Append to `backend/pyproject.toml`:
```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "mealcycle.settings"
python_files = ["test_*.py"]
```
Create `backend/conftest.py` (empty for now; Task 4 adds fixtures):
```python
"""Shared pytest fixtures, discovered automatically by pytest."""
```
Create an empty `backend/mealcycle/tests/__init__.py`.

- [ ] **Step 2: Write the failing env-helper tests**

`backend/mealcycle/tests/test_env.py`:
```python
import pytest
from django.core.exceptions import ImproperlyConfigured

from mealcycle.env import env_list, env_required


def test_env_required_returns_value(monkeypatch):
    monkeypatch.setenv("MEALCYCLE_TEST_VAR", "hello")
    assert env_required("MEALCYCLE_TEST_VAR") == "hello"


def test_env_required_raises_clear_error_when_missing(monkeypatch):
    monkeypatch.delenv("MEALCYCLE_TEST_VAR", raising=False)
    with pytest.raises(ImproperlyConfigured, match="MEALCYCLE_TEST_VAR"):
        env_required("MEALCYCLE_TEST_VAR")


def test_env_required_treats_empty_as_missing(monkeypatch):
    monkeypatch.setenv("MEALCYCLE_TEST_VAR", "")
    with pytest.raises(ImproperlyConfigured, match="MEALCYCLE_TEST_VAR"):
        env_required("MEALCYCLE_TEST_VAR")


def test_env_list_strips_spaces_and_drops_empties(monkeypatch):
    monkeypatch.setenv("MEALCYCLE_TEST_LIST", " localhost, 127.0.0.1,, ")
    assert env_list("MEALCYCLE_TEST_LIST") == ["localhost", "127.0.0.1"]


def test_env_list_returns_empty_list_when_unset(monkeypatch):
    monkeypatch.delenv("MEALCYCLE_TEST_LIST", raising=False)
    assert env_list("MEALCYCLE_TEST_LIST") == []
```

- [ ] **Step 3: Run them to confirm they fail**

```bash
cd ~/Sites/mealcycle/backend
venv/bin/pytest mealcycle/tests/test_env.py -v
```
Expected: collection error `ModuleNotFoundError: No module named 'mealcycle.env'`.

- [ ] **Step 4: Implement `backend/mealcycle/env.py`**

```python
"""Helpers for reading configuration from environment variables."""

import os

from django.core.exceptions import ImproperlyConfigured


def env_required(name: str) -> str:
    """Return the variable's value, or fail loudly if it is missing or empty."""
    value = os.environ.get(name)
    if not value:
        raise ImproperlyConfigured(f"Missing required environment variable: {name}")
    return value


def env_list(name: str) -> list[str]:
    """Parse a comma-separated variable into a list, ignoring blanks."""
    raw = os.environ.get(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]
```

- [ ] **Step 5: Run the tests to confirm they pass**

```bash
venv/bin/pytest mealcycle/tests/test_env.py -v
```
Expected: 5 passed.

- [ ] **Step 6: Create the database and the local `.env`**

```bash
createdb -h localhost -U postgres mealcycle
psql -h localhost -U postgres -Atc "select datname from pg_database where datname='mealcycle'"
SECRET=$(venv/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
cat > .env <<EOF
SECRET_KEY='${SECRET}'
DEBUG='True'
ALLOWED_HOSTS='localhost,127.0.0.1'
DATABASE_URL='postgres://postgres@localhost:5432/mealcycle'
ANTHROPIC_API_KEY='your-anthropic-api-key-here'
EOF
cd .. && git status --short backend/.env; cd backend
```
Expected: `psql` prints `mealcycle`. `git status` prints **nothing** for `.env`, which proves it's gitignored. (The single quotes stop python-dotenv from interpreting `$` and `#` inside the generated key.)

- [ ] **Step 7: Update `backend/.env.example`**

Replace the whole file:
```
# Copy to .env and fill in. Never commit .env.
# Generate a key: venv/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY='change-me'
DEBUG='True'
ALLOWED_HOSTS='localhost,127.0.0.1'
DATABASE_URL='postgres://postgres@localhost:5432/mealcycle'
ANTHROPIC_API_KEY='your-anthropic-api-key-here'
```

- [ ] **Step 8: Write the failing database test**

`backend/mealcycle/tests/test_database.py`:
```python
import pytest
from django.db import connection


@pytest.mark.django_db
def test_database_is_postgres():
    assert connection.vendor == "postgresql"
```
Run: `venv/bin/pytest mealcycle/tests/test_database.py -v`
Expected: FAIL, `AssertionError: assert 'sqlite' == 'postgresql'`.

- [ ] **Step 9: Rewrite the top of `settings.py` to use env vars**

In `backend/mealcycle/settings.py`, replace the imports, the `SECRET_KEY` / `DEBUG` / `ALLOWED_HOSTS` block and the `DATABASES` block. Final versions of those parts:

```python
import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

from mealcycle.env import env_list, env_required

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load backend/.env if it exists. Real environment variables take priority,
# so production and CI never need a .env file.
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = env_required("SECRET_KEY")

DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS")
```
Then:
```python
DATABASES = {
    "default": dj_database_url.parse(env_required("DATABASE_URL")),
}
```
Delete the old hard-coded `SECRET_KEY = 'django-insecure-...'` line and the SQLite `DATABASES` dict completely.

- [ ] **Step 10: Run all tests and checks**

```bash
venv/bin/pytest -v
venv/bin/python manage.py check
venv/bin/ruff format . && venv/bin/ruff check . && venv/bin/ruff format --check .
grep -n "django-insecure" mealcycle/settings.py || echo "old key removed"
```
Expected: 6 passed; `no issues`; ruff clean; `old key removed`. **Do not run `migrate`.**

- [ ] **Step 11: Check the missing-variable error manually**

```bash
SECRET_KEY= venv/bin/python manage.py check 2>&1 | tail -1
```
Expected: `django.core.exceptions.ImproperlyConfigured: Missing required environment variable: SECRET_KEY` (an empty env var in the shell overrides `.env` and counts as missing).

- [ ] **Step 12: Learning notes**

Add notes on: modules and `import` / `from x import y` (≈ `use`), type hints (`name: str -> str`), f-strings (≈ `"{$var}"`), list comprehensions, `raise` (≈ `throw`), pytest's `monkeypatch` fixture, `@pytest.mark.django_db`, and Postgres's `createdb`.

- [ ] **Step 13: Commit**

```bash
cd ~/Sites/mealcycle
git add backend/mealcycle backend/conftest.py backend/pyproject.toml backend/.env.example docs/learning
git commit -m "feat(backend): load settings from env and switch to Postgres

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012zGs6upQQTHmFkBVt2UXNh"
```

---

### Task 3: `accounts` app: email-only custom User

Deliverable: `accounts.User` is the auth model, the first migrations are applied to the `mealcycle` database, the admin works with email login, and all User tests pass.

**Files:**
- Create (via `startapp`, then edited): `backend/accounts/__init__.py`, `apps.py`, `models.py`, `admin.py`, `migrations/0001_initial.py`, `tests/__init__.py`, `tests/test_models.py`, `tests/test_admin.py`
- Delete: `backend/accounts/tests.py`, `backend/accounts/views.py` (generated stubs; tests go in `tests/`, and this app has no views yet)
- Modify: `backend/mealcycle/settings.py` (`INSTALLED_APPS`, `AUTH_USER_MODEL`)

**Interfaces:**
- Produces: `accounts.models.User` with fields `email`, `is_active`, `is_staff`, `date_joined` (+ `password`, `last_login`, `is_superuser`, `groups`, `user_permissions`). `User.objects.create_user(email: str, **extra_fields) -> User`; `User.objects.create_superuser(email: str, password: str | None, **extra_fields) -> User`; `accounts.models.normalize_email_address(email: str) -> str`.

- [ ] **Step 1: Create the app and register it**

```bash
cd ~/Sites/mealcycle/backend
venv/bin/python manage.py startapp accounts
rm accounts/tests.py accounts/views.py
mkdir accounts/tests && touch accounts/tests/__init__.py
```
In `settings.py`, add `"accounts",` at the end of `INSTALLED_APPS`, and add below `INSTALLED_APPS`:
```python
AUTH_USER_MODEL = "accounts.User"
```

- [ ] **Step 2: Write the failing model tests**

`backend/accounts/tests/test_models.py`:
```python
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
```

- [ ] **Step 3: Run them to confirm they fail**

```bash
venv/bin/pytest accounts -v
```
Expected: an error mentioning `cannot import name 'User' from 'accounts.models'`, or Django refusing to start because `AUTH_USER_MODEL refers to model 'accounts.User' that has not been installed`.

- [ ] **Step 4: Implement `backend/accounts/models.py`**

```python
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
```

- [ ] **Step 5: Generate the first migration**

```bash
venv/bin/python manage.py makemigrations accounts
```
Expected: `Migrations for 'accounts': accounts/migrations/0001_initial.py - Create model User`.

- [ ] **Step 6: Run the model tests to confirm they pass**

```bash
venv/bin/pytest accounts -v
```
Expected: 10 passed.

- [ ] **Step 7: Write the failing admin tests**

`backend/accounts/tests/test_admin.py`:
```python
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
```
(`admin_client` and `admin_user` are fixtures from pytest-django: a test client already logged in as a superuser.)

Run: `venv/bin/pytest accounts/tests/test_admin.py -v`
Expected: `test_user_changelist_loads` and the add/change tests FAIL with 404 (the model isn't registered in the admin yet). The login test may already pass, which is fine: it pins `get_by_natural_key` from Step 4.

- [ ] **Step 8: Implement `backend/accounts/admin.py`**

```python
from django.contrib import admin

from accounts.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    # Plain ModelAdmin on purpose: Django's built-in UserAdmin assumes a
    # username and password forms, and our app users are passwordless.
    list_display = ("email", "is_active", "is_staff", "date_joined")
    search_fields = ("email",)
    list_filter = ("is_active", "is_staff")
    ordering = ("email",)
    fields = (
        "email",
        "is_active",
        "is_staff",
        "is_superuser",
        "groups",
        "user_permissions",
        "date_joined",
        "last_login",
    )
    readonly_fields = ("date_joined", "last_login")
    filter_horizontal = ("groups", "user_permissions")
```
Run: `venv/bin/pytest accounts -v`
Expected: 14 passed.

- [ ] **Step 9: Apply migrations to the real database (first time)**

```bash
psql -h localhost -U postgres -d mealcycle -Atc "select count(*) from information_schema.tables where table_schema='public'"
venv/bin/python manage.py migrate
psql -h localhost -U postgres -d mealcycle -Atc "\dt accounts_*"
```
Expected: first count `0` (empty database). `migrate` ends with `Applying sessions.0001_initial... OK`. The last command lists `accounts_user`, `accounts_user_groups` and `accounts_user_user_permissions`, and there is **no** `auth_user` table.

- [ ] **Step 10: Create your admin account (interactive, the user runs this)**

The user runs this in the prompt themselves:
```
! cd ~/Sites/mealcycle/backend && venv/bin/python manage.py createsuperuser
```
Expected: it asks for **Email address** and **Password** only. There's no username prompt.

- [ ] **Step 11: Full checks**

```bash
venv/bin/pytest -v
venv/bin/python manage.py makemigrations --check --dry-run
venv/bin/ruff format . && venv/bin/ruff check . && venv/bin/ruff format --check .
```
Expected: 20 passed; `No changes detected`; ruff clean.

- [ ] **Step 12: Learning notes**

Add notes on: classes, inheritance with parentheses, multiple inheritance/mixins (≈ traits), `self` (≈ `$this`), `super().save()` (≈ `parent::save()`), `*args, **kwargs` (≈ `...$args` / named args), `__str__` (≈ `__toString`), managers (`User.objects` ≈ Eloquent static methods), `makemigrations` vs `migrate` (Django *generates* migrations from models; Laravel has you write them), `AUTH_USER_MODEL`, and decorators (`@admin.register`).

- [ ] **Step 13: Commit**

```bash
cd ~/Sites/mealcycle
git add backend/accounts backend/mealcycle/settings.py docs/learning
git commit -m "feat(accounts): add email-only passwordless custom User model

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012zGs6upQQTHmFkBVt2UXNh"
```

---

### Task 4: DRF, `/api/v1/` and the health check

Deliverable: `GET /api/v1/health/` returns 200 when the DB is up and 503 when it's down. DRF defaults to authenticated-only.

**Files:**
- Create (via `startapp`, then trimmed): `backend/core/__init__.py`, `apps.py`, `views.py`, `urls.py`, `tests/__init__.py`, `tests/test_health.py`
- Delete: `backend/core/tests.py`, `admin.py`, `models.py`, `migrations/` (core has no models)
- Modify: `backend/mealcycle/settings.py`, `backend/mealcycle/urls.py`, `backend/conftest.py`

**Interfaces:**
- Consumes: `DEBUG` from settings (Task 2).
- Produces: URL `/api/v1/health/` (name `health`); `api_client` pytest fixture returning `rest_framework.test.APIClient`; `mealcycle/urls.py` includes `core.urls` under `api/v1/`, where later sub-projects add their own `include()`s.

- [ ] **Step 1: Create the app and trim it**

```bash
cd ~/Sites/mealcycle/backend
venv/bin/python manage.py startapp core
rm -r core/tests.py core/admin.py core/models.py core/migrations
mkdir core/tests && touch core/tests/__init__.py
```

- [ ] **Step 2: Add the `api_client` fixture**

Replace `backend/conftest.py`:
```python
"""Shared pytest fixtures, discovered automatically by pytest."""

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """An unauthenticated DRF test client."""
    return APIClient()
```

- [ ] **Step 3: Write the failing health tests**

`backend/core/tests/test_health.py`:
```python
from unittest.mock import patch

import pytest
from django.db import OperationalError

pytestmark = pytest.mark.django_db

HEALTH_URL = "/api/v1/health/"


def test_health_ok_without_login(api_client):
    response = api_client.get(HEALTH_URL)
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_is_down(api_client):
    with patch("core.views.connection") as mock_connection:
        mock_connection.ensure_connection.side_effect = OperationalError("db down")
        response = api_client.get(HEALTH_URL)
    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "unavailable"}


def test_health_rejects_post(api_client):
    response = api_client.post(HEALTH_URL)
    assert response.status_code == 405
```
Run: `venv/bin/pytest core -v`
Expected: FAIL. The 200 test gets 404 (no URL yet); the mock test errors because `core.views` has no `connection`.

- [ ] **Step 4: Configure DRF in `settings.py`**

Add `"rest_framework",` and `"core",` to `INSTALLED_APPS` (order: Django apps, then `"rest_framework"`, then `"accounts"`, `"core"`). Add at the end of the file:
```python
# Django REST Framework
# Every endpoint requires login unless it explicitly opts out.
# JWT for the mobile app arrives in the auth sub-project.
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        # Clickable HTML API pages, only while developing.
        *(["rest_framework.renderers.BrowsableAPIRenderer"] if DEBUG else []),
    ],
}
```

- [ ] **Step 5: Implement `backend/core/views.py`**

```python
from django.db import OperationalError, connection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Liveness check for hosting platforms and uptime monitors."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        try:
            connection.ensure_connection()
        except OperationalError:
            return Response(
                {"status": "error", "database": "unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"status": "ok", "database": "ok"})
```

- [ ] **Step 6: Wire up the URLs**

Create `backend/core/urls.py`:
```python
from django.urls import path

from core.views import HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
]
```
Replace `backend/mealcycle/urls.py`:
```python
"""Root URL configuration. Each app's routes are included under /api/v1/."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("core.urls")),
]
```

- [ ] **Step 7: Run the health tests to confirm they pass**

```bash
venv/bin/pytest core -v
```
Expected: 3 passed.

- [ ] **Step 8: Try it for real**

```bash
venv/bin/python manage.py runserver 8000 &
sleep 2
curl -s localhost:8000/api/v1/health/; echo
curl -s -o /dev/null -w "%{http_code}\n" -X POST localhost:8000/api/v1/health/
kill %1
```
Expected: `{"status":"ok","database":"ok"}` and `405`. (Opening http://localhost:8000/api/v1/health/ in a browser shows the browsable API page, because `DEBUG=True`.)

- [ ] **Step 9: Full checks**

```bash
venv/bin/pytest -v
venv/bin/python manage.py makemigrations --check --dry-run
venv/bin/ruff format . && venv/bin/ruff check . && venv/bin/ruff format --check .
```
Expected: 23 passed; `No changes detected`; ruff clean.

- [ ] **Step 10: Learning notes**

Add notes on: the DRF request lifecycle (urls → view → Response), `APIView` and method-per-verb (≈ a Laravel controller), `as_view()`, `include()` (≈ `Route::prefix()->group()`), `try/except` (≈ `try/catch`), `unittest.mock.patch` and `side_effect` (≈ Mockery), pytest fixtures and `conftest.py`, and the `*( ... )` unpacking used in the renderer list.

- [ ] **Step 11: Commit**

```bash
cd ~/Sites/mealcycle
git add backend/core backend/conftest.py backend/mealcycle docs/learning
git commit -m "feat(core): configure DRF and add /api/v1/health/ endpoint

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012zGs6upQQTHmFkBVt2UXNh"
```

---

### Task 5: CI, docs, pull request

Deliverable: GitHub Actions runs lint, format check, migration check and tests on the PR and passes. CLAUDE.md shows the new workflow.

**Files:**
- Create: `.github/workflows/backend.yml`
- Modify: `CLAUDE.md` (Project Structure, Running the Backend), `docs/foundation/decisions.md` / `docs/README.md` (status → Implemented)

**Interfaces:**
- Consumes: `backend/.python-version` (Task 1), `requirements-dev.txt` (Task 1), env var names (Task 2).

- [ ] **Step 1: Create `.github/workflows/backend.yml`**

```yaml
name: Backend CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend

    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: mealcycle
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    env:
      SECRET_KEY: ci-only-not-a-real-secret
      DEBUG: "False"
      DATABASE_URL: postgres://postgres:postgres@localhost:5432/mealcycle

    steps:
      - uses: actions/checkout@v5

      - uses: actions/setup-python@v6
        with:
          python-version-file: backend/.python-version
          cache: pip
          cache-dependency-path: |
            backend/requirements.txt
            backend/requirements-dev.txt

      - name: Install dependencies
        run: pip install -r requirements-dev.txt

      - name: Lint
        run: ruff check .

      - name: Check formatting
        run: ruff format --check .

      - name: Check for missing migrations
        run: python manage.py makemigrations --check --dry-run

      - name: Run tests
        run: pytest
```

- [ ] **Step 2: Update `CLAUDE.md`**

Replace the Project Structure block with:
```
mealcycle/
├── .github/workflows/  # CI (backend.yml)
├── backend/            # Django REST API (Python 3.13)
│   ├── mealcycle/      # Project settings, root urls, env helpers
│   ├── accounts/       # Custom User model (email-only, passwordless)
│   ├── core/           # Project-wide features (health check)
│   ├── venv/           # Python virtual environment (gitignored)
│   ├── manage.py
│   ├── pyproject.toml  # pytest + ruff config
│   ├── requirements.txt
│   └── requirements-dev.txt
├── docs/               # Per-domain context, decisions, specs, plans
└── frontend/           # Mobile app (to be added)
```
Replace the "Running the Backend" section with:
````markdown
## Running the Backend

First-time setup:
```bash
cd backend
pyenv install --skip-existing "$(cat .python-version)"
python -m venv venv
venv/bin/pip install -r requirements-dev.txt
cp .env.example .env            # then set SECRET_KEY
createdb -h localhost -U postgres mealcycle
venv/bin/python manage.py migrate
venv/bin/python manage.py createsuperuser
```

Daily:
```bash
cd backend
source venv/bin/activate
python manage.py runserver      # http://localhost:8000/api/v1/health/
pytest                          # tests
ruff check . && ruff format .   # lint + format (run before every PR)
```
````

- [ ] **Step 3: Mark the foundation as implemented in the docs**

In `docs/README.md`, change the Foundation status to `Implemented`. In `docs/foundation/spec.md`, change `**Status:** Approved` to `**Status:** Implemented`.

- [ ] **Step 4: Commit**

```bash
cd ~/Sites/mealcycle
git add .github CLAUDE.md docs
git commit -m "ci: add backend GitHub Actions workflow; update setup docs

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012zGs6upQQTHmFkBVt2UXNh"
```

- [ ] **Step 5: Push and open the PR**

```bash
git push -u origin feature/foundation
gh pr create --base main --title "Backend foundation: env settings, Postgres, email-only User, DRF, health check, CI" --body-file - <<'EOF'
## What changed
- Python 3.13 + pinned dependencies (`requirements.txt` / `requirements-dev.txt`); psycopg 3 replaces psycopg2
- Settings read from environment (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`); the committed secret key is removed
- Postgres replaces SQLite
- `accounts` app: email-only, passwordless custom `User` (admin superuser keeps a password)
- DRF configured (authenticated by default), routes under `/api/v1/`
- `core` app: `GET /api/v1/health/` (200 / 503)
- pytest + ruff config in `pyproject.toml`; GitHub Actions CI
- `docs/`: per-domain context, decisions, foundation spec and plan, Python learning notes

## Why
Sub-project 1 of the backend roadmap (`docs/product/overview.md`). The custom User model has to exist before the first migration, and every later feature builds on this base. Full reasoning: `docs/foundation/decisions.md`.

## How to test
```bash
cd backend
venv/bin/pip install -r requirements-dev.txt
cp .env.example .env   # set SECRET_KEY
createdb -h localhost -U postgres mealcycle
venv/bin/python manage.py migrate
venv/bin/pytest
venv/bin/python manage.py runserver
curl localhost:8000/api/v1/health/   # {"status":"ok","database":"ok"}
```
`createsuperuser` asks only for email + password; log in at `/admin/`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_012zGs6upQQTHmFkBVt2UXNh
EOF
```
Expected: a PR URL is printed.

- [ ] **Step 6: Watch CI**

```bash
gh pr checks --watch
```
Expected: `Backend CI / test` passes. If it fails, read the log (`gh run view --log-failed`), fix it, commit and push again.
