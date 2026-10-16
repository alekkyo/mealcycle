# Foundation: Design Spec

**Status:** Approved · **Date:** 2026-10-17 · **Sub-project:** 1 of 7 (see [product/overview.md](../product/overview.md))

Decisions and their reasoning are in [decisions.md](decisions.md). This spec describes **what gets built**.

## Goal

Turn the untouched `startproject` scaffold into a production-ready base: secrets come from the environment, Postgres is the database, there's an email-only custom User model, DRF is configured, and tests, linting and CI run on every PR. It ends with one working public endpoint (`/api/v1/health/`) that proves the whole stack works.

## Out of scope

Login flows (email code/link, Apple, Google, JWT), user profiles, the trial, onboarding, Docker, and deployment. Those belong to later sub-projects.

## 1. Runtime and dependencies

- **Python 3.13** via pyenv. `backend/.python-version` contains `3.13` (≈ `.nvmrc`), so pyenv picks it automatically inside `backend/`.
- `backend/venv/` is deleted and recreated on 3.13.
- **`backend/requirements.txt`** (production), pinned to exact versions at install time:
  - `Django` (5.2.x LTS), `djangorestframework`, `psycopg[binary]` (v3, replaces `psycopg2-binary`), `python-dotenv`, `dj-database-url`
- **`backend/requirements-dev.txt`**: starts with `-r requirements.txt`, then `pytest`, `pytest-django`, `ruff`.

## 2. Configuration (`mealcycle/settings.py`)

Kept as one settings file. Values that differ between environments come from env vars, and `backend/.env` is loaded with `python-dotenv` if it exists.

| Variable | Required | Default | Notes |
|---|---|---|---|
| `SECRET_KEY` | **yes** | none, so startup fails if missing | A newly generated key. The committed one is removed and treated as leaked |
| `DEBUG` | no | `False` | Only the exact string `"True"` turns it on |
| `ALLOWED_HOSTS` | no | empty | Comma-separated list |
| `DATABASE_URL` | **yes** | none | Parsed by `dj-database-url` |

- `backend/.env.example` is updated to list exactly these four variables, plus the existing `ANTHROPIC_API_KEY` placeholder. `backend/.env` is created locally and stays gitignored.
- SQLite config is removed.

## 3. Database

- A new database `mealcycle` on the local PostgreSQL 17 (DBngin, `localhost:5432`, user `postgres`). Other databases on that server are not touched.
- Local `DATABASE_URL=postgres://postgres@localhost:5432/mealcycle`
- pytest-django creates and destroys `test_mealcycle` automatically.
- Migrations are generated and committed (as CLAUDE.md requires).

## 4. `accounts` app: custom User

**`accounts/models.py`**
- `UserManager(BaseUserManager)`
  - `create_user(email, **extra)`: raises `ValueError` if the email is empty, lowercases the whole email, calls `set_unusable_password()`, saves.
  - `create_superuser(email, password, **extra)`: same, but with a real password and `is_staff=True`, `is_superuser=True`.
- `User(AbstractBaseUser, PermissionsMixin)`
  - `email`: `EmailField(unique=True)`, `USERNAME_FIELD = "email"`, `REQUIRED_FIELDS = []`
  - `is_active` (default `True`), `is_staff` (default `False`), `date_joined` (default `timezone.now`)
  - `save()` also normalizes the email (strips spaces, lowercases) and, **if no password is set, calls `set_unusable_password()`**, so every way of creating a user gets the same treatment, including the admin form. (Django treats an empty password string as *usable*, so this step is needed.) Uniqueness is then enforced by the database's unique constraint.
  - `get_by_natural_key()` normalizes too, so the admin login accepts `Alex@Example.com`.
- `settings.AUTH_USER_MODEL = "accounts.User"`, set **before the first `migrate`**.

**`accounts/admin.py`**: `UserAdmin(admin.ModelAdmin)`, deliberately not Django's built-in `UserAdmin`, which assumes a `username` and password forms.
- `list_display` (email, is_active, is_staff, date_joined), `search_fields` (email), `list_filter` (is_active, is_staff)
- Editable fields: email, is_active, is_staff, is_superuser, groups, user_permissions. `date_joined` and `last_login` are read-only. `password` is **excluded** from the form, so the admin never shows or edits hashes.
- Users created in the admin go through `save()` with no password set, so `save()` gives them an unusable password and they're passwordless like app users. The admin superuser is created only with `createsuperuser`.

## 5. DRF and URLs

`INSTALLED_APPS` gains `rest_framework`, `accounts` and `core`.

```python
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_RENDERER_CLASSES": [JSONRenderer] + ([BrowsableAPIRenderer] if DEBUG else []),
}
```

**URL layout**

```
/admin/           → Django admin
/api/v1/          → include("core.urls")      (later sub-projects add their apps here)
/api/v1/health/   → core.views.HealthView
```

## 6. `core` app: health check

`core/views.py`: `HealthView(APIView)`, `permission_classes = [AllowAny]`, `authentication_classes = []`.

- `get()`: calls `django.db.connection.ensure_connection()`.
  - On success: `200 {"status": "ok", "database": "ok"}`
  - On `django.db.OperationalError`: `503 {"status": "error", "database": "unavailable"}`
- Other HTTP verbs return `405` (DRF does this automatically).

## 7. Tests (pytest + pytest-django)

- Layout: `accounts/tests/test_models.py`, `core/tests/test_health.py`, with shared fixtures (`api_client`) in `backend/conftest.py`.
- **accounts**
  - `create_user` stores the email in lowercase, and `has_usable_password()` is `False`
  - creating a user with a duplicate email, including different upper/lower case, raises `IntegrityError`
  - an empty email raises `ValueError`
  - `create_superuser` gives a usable password, `is_staff` and `is_superuser`
- **core**
  - `GET /api/v1/health/` returns 200 with the exact body, without being logged in
  - with `ensure_connection` mocked to raise `OperationalError`, it returns 503 with the exact body
  - `POST` returns 405

## 8. Linting and formatting (ruff)

All tool configuration lives in `backend/pyproject.toml`:
- `[tool.pytest.ini_options]`: `DJANGO_SETTINGS_MODULE = "mealcycle.settings"`
- `[tool.ruff]`: target `py313`, line length 88 (ruff's default), `migrations` folders excluded
- `[tool.ruff.lint]` rules: `E`, `W`, `F` (errors), `I` (import sorting), `B` (bug patterns), `UP` (modern syntax), `DJ` (Django). `E501` (line too long) is ignored because the formatter handles line length

All existing files must pass `ruff check` and `ruff format --check`.

## 9. CI (GitHub Actions)

`.github/workflows/backend.yml`
- Runs on: `pull_request`, and `push` to `main`. Working directory: `backend/`.
- Job runs on `ubuntu-latest` with a `postgres:17` service container.
- Env: a throwaway CI-only `SECRET_KEY`, and a `DATABASE_URL` pointing at the service container.
- Steps:
  1. Check out the code
  2. Set up Python 3.13, with the pip cache keyed on the requirements files
  3. `pip install -r requirements-dev.txt`
  4. `ruff check .`
  5. `ruff format --check .`
  6. `python manage.py makemigrations --check --dry-run`, which fails if someone changed a model and forgot to commit the migration
  7. `pytest`

## 10. Housekeeping

- `.gitignore`: add `.pytest_cache/` and `.ruff_cache/`.
- `CLAUDE.md`: update "Running the Backend" (Python 3.13, `.env` setup, install from `requirements-dev.txt`, `migrate`, `pytest`, `ruff`) and the Project Structure tree (`accounts/`, `core/`, `docs/`).
- `docs/learning/python-for-laravel-devs.md`: add notes for each new concept as it comes up during implementation.

## Done when

- [ ] `python --version` inside `backend/` shows 3.13.x, and the venv is rebuilt on it
- [ ] `python manage.py migrate` succeeds against the `mealcycle` Postgres database
- [ ] `python manage.py createsuperuser` asks for an email and password only (no username), and that account can log into `/admin/`
- [ ] `curl localhost:8000/api/v1/health/` returns `{"status": "ok", "database": "ok"}`
- [ ] `pytest`, `ruff check .`, `ruff format --check .` and `makemigrations --check` all pass locally and in CI
- [ ] No secret is committed. `SECRET_KEY` only exists in `.env` and as the CI placeholder
