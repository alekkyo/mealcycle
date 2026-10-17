# Python for a Laravel Developer

Notes from our discussions, written for someone who knows PHP/Laravel, TypeScript, a little Go, React, and Vue.

## Laravel → Django vocabulary

| Laravel | Django / Python |
|---|---|
| `php artisan` | `python manage.py` |
| `composer` | `pip` |
| `vendor/` | `venv/` (virtual environment) |
| `composer.json` / `composer.lock` | `requirements.txt` |
| `config/` folder | `settings.py` |
| `routes/api.php` | `urls.py` (project root + one per app) |
| Controllers | **Views** (DRF class-based views) |
| API Resources + Form Requests | **Serializers** (format output *and* validate input) |
| Eloquent models | Django models (ORM) |
| Migrations | Migrations (generated with `makemigrations`, applied with `migrate`) |
| Modules / packages | **Apps**: self-contained feature folders (models, views, urls, migrations) |
| Nova / Filament | Django admin (built in) |

Django calls its pattern **MVT** (Model–View–Template). It's MVC under different names. We're building a JSON API, so templates are replaced by serializers.

## Virtual environments (venv)

A venv is a **private copy of Python plus its packages** for one project. All our packages live in:

```
backend/venv/lib/python3.10/site-packages/
```

`venv/` is gitignored, like `vendor/`. You can always recreate it:

```bash
python -m venv venv
venv/bin/pip install -r requirements.txt     # like `composer install`
```

### What "activating" means

`source venv/bin/activate` runs a small shell script that:
1. sets `VIRTUAL_ENV` to the venv's path
2. **puts `venv/bin` at the front of `PATH`**, so `python`, `pip` and `django-admin` now point to the venv's copies
3. adds `(venv)` to your prompt
4. defines a `deactivate` command that undoes all of this

```
Before:  python → ~/.pyenv/shims/python3                     (global)
After:   python → ~/Sites/mealcycle/backend/venv/bin/python  (project)
```

Things to know:
- **`source` is required.** It runs the script in your *current* shell. Without it, the changes happen in a child process and disappear immediately.
- **Nothing is saved.** It only affects that one terminal tab, and it goes away on `deactivate` or when you close the tab. Your `~/.zshrc` and other tabs aren't touched.
- **You can use the terminal for anything else.** `git`, `npm`, `php` and so on work normally. Only the commands in `venv/bin` are affected.
- **Watch out:** if you `cd` into a *different* Python project while this venv is active, `pip install` installs into the wrong project. Run `deactivate` first, or use a new tab.
- **It's optional.** `venv/bin/python manage.py runserver` does the same thing without activating.
- **Why PHP doesn't need this:** Composer's autoloader always loads from `./vendor`. Python loads packages relative to *the interpreter that's running*, and activating is how you choose that interpreter.

### Daily workflow

```bash
cd ~/Sites/mealcycle/backend
source venv/bin/activate        # once per new terminal tab
python manage.py runserver
```

To avoid typing this: point VS Code/PyCharm at `backend/venv/bin/python` and they'll activate it for you, or use `direnv` to activate automatically when you `cd` into the folder.

### Gotcha: `requirements.txt` isn't updated for you

Unlike `composer require`, `pip install foo` does **not** add `foo` to `requirements.txt`. Add it by hand with the exact version (`foo==1.2.3`), or run `pip freeze > requirements.txt`.

## Python tooling you'll see at work

| Tool | What it is | Where it's used |
|---|---|---|
| **venv + pip** | Built-in baseline (what we use) | Everywhere, and in tutorials |
| **uv** | Fast all-in-one tool with `pyproject.toml` + `uv.lock`. `uv run …` means no activation needed | New projects, growing fast |
| **Poetry** | Lockfile + automatic venvs (`poetry add` ≈ `composer require`) | Many existing codebases |
| **pipenv** | An older attempt at the same idea | Older projects |
| **conda** | Also manages non-Python libraries | Data science / ML |
| **Docker** | Python runs in a container | Many dev setups, and almost all deployments |

Ask the new team which one they use.

## `.env` files and settings

Same idea as Laravel's `.env`, with one difference: **Django doesn't load `.env` by itself.** Laravel reads it automatically. In Django, `settings.py` is plain Python, so we load the file ourselves using the `python-dotenv` package:

```python
# settings.py
import os                          # Python's built-in module for talking to the OS (≈ getenv() in PHP)
from dotenv import load_dotenv     # from the python-dotenv package

load_dotenv(BASE_DIR / ".env")     # reads backend/.env into the process's environment variables

SECRET_KEY = os.environ["SECRET_KEY"]                  # required: crashes on startup if it's missing
DEBUG = os.environ.get("DEBUG", "False") == "True"     # optional, with a default (≈ env('DEBUG', false))
```

- `os.environ["X"]` fails loudly if `X` is missing. Good for values that must be set, like secrets.
- `os.environ.get("X", default)` is like Laravel's `env('X', default)`.
- Environment variables are **always strings**, so `"True"` has to be converted to the boolean `True` explicitly.
- `.env` is gitignored, and `.env.example` is committed as a template. Same as Laravel.
- `DATABASE_URL` packs the whole connection into one string (`postgres://user:pass@host:port/db`). A small package, `dj-database-url`, turns it into Django's `DATABASES` dict.
- In production we don't use a `.env` file. The hosting platform sets real environment variables, and `load_dotenv` does nothing if the file isn't there.

## `INSTALLED_APPS`: "registering" a package

`INSTALLED_APPS` in `settings.py` is the list of apps that Django turns on. It's roughly Laravel's list of service providers. **`pip install` only downloads code. Listing the app in `INSTALLED_APPS` is what makes Django actually use it** (its models, migrations, templates, admin and management commands).

```python
INSTALLED_APPS = [
    "django.contrib.admin",       # Django's own features are apps too
    "django.contrib.auth",
    ...
    "rest_framework",             # ← "registering DRF"
    "accounts",                   # ← our own apps get listed here as well
]
```

Package-wide settings go in a dict (≈ a `config/*.php` file returning an array):

```python
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],  # login required by default
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],         # JSON responses only
}
```

**DRF (Django REST Framework)** is the package that turns Django into an API framework. Django on its own is built for server-rendered HTML pages. DRF adds serializers, API views, authentication classes, permissions and pagination: everything Laravel gives you for API routes.

## psycopg: the Postgres driver

**psycopg** (pronounced "psycho-P-G") is the library Python uses to talk to PostgreSQL. In PHP terms it's the **`pdo_pgsql` extension**: the low-level piece that opens a connection, sends SQL and returns rows.

```
Your code:   User.objects.filter(email="a@b.com")      (≈ Eloquent)
                 ↓  Django ORM builds SQL
             SELECT ... FROM accounts_user WHERE email = 'a@b.com'
                 ↓  psycopg sends it over the network
             PostgreSQL on localhost:5432
```

- You almost never call psycopg directly. Django's ORM uses it underneath. Django picks it because `DATABASES` says `ENGINE: django.db.backends.postgresql`.
- **Versions:** `psycopg2` is the long-time standard. `psycopg` (version 3, without the "2" in the name) is its modern successor, and it's what Django recommends now. We use v3.
- **`[binary]`:** psycopg is built on `libpq`, Postgres's official C library. `pip install "psycopg[binary]"` installs a pre-compiled copy, so you don't need a C compiler or Postgres headers on your machine. It's the same idea as the old `psycopg2-binary` package.
- Every database has its own driver: `mysqlclient` for MySQL, and `sqlite3` is built into Python, which is why the scaffold's SQLite setup needed no extra package.

## Django admin

A **back-office web UI that's built in and generated automatically** from your models, at `/admin/`. It's like **Laravel Nova or Filament**, but it's included free in every Django project. The scaffold's `urls.py` already has `path('admin/', admin.site.urls)`.

- **It's for us (staff), not for app users.** You use it to look up a user, check their onboarding answers, fix bad data or disable an account, without writing SQL or building internal tools.
- **It's generated from models.** You register a model and get list, search, filter, create, edit and delete pages:

```python
# accounts/admin.py
from django.contrib import admin
from .models import User

@admin.register(User)                 # "@" is a decorator: it registers the class below with the admin
class UserAdmin(admin.ModelAdmin):
    list_display = ["email", "is_active", "is_staff", "date_joined"]   # table columns
    search_fields = ["email"]                                          # search box
    list_filter = ["is_active", "is_staff"]                            # sidebar filters
```

- **Login uses email + password**, through ordinary Django sessions (cookies). That's why the superuser account (`python manage.py createsuperuser`) is the one account with a real password, while app users are passwordless.
- **Who can log in:** only users with `is_staff=True`. What they can do depends on `is_superuser` (everything) or individual permissions.
- **For production:** use a strong password, consider a non-obvious URL instead of `/admin/`, and maybe restrict access by IP or add 2FA. We'll cover that when we deploy.

## pyenv and `.python-version`

**pyenv** manages several Python versions on one machine, like **nvm** for Node. `pyenv install 3.13.16` downloads Python's source code and **compiles** it (which is why it takes a few minutes). Each version lives in `~/.pyenv/versions/<version>/`.

`pyenv local 3.13.16` writes a **`.python-version`** file (≈ `.nvmrc`). Inside that folder, the `python` command now means 3.13.16. Outside it, you get the global version (3.10.3 on this Mac). CI reads the same file, so local and CI always use the same version.

Order of operations:
1. pyenv provides the interpreter (`python` = 3.13.16 inside `backend/`)
2. `python -m venv venv` creates a venv **from that interpreter**, so the venv is permanently 3.13.16
3. after that, the venv's own `venv/bin/python` is what we use

`python -m <module>` means "run this module as a script". `python -m venv`, `python -m pip` and `python -m pytest` are common examples.

## Pinning versions: `==` and `pip freeze`

- `pip install "Django>=5.2,<5.3"` says "any 5.2.x". It's like Composer's `~5.2.0`, and the quotes stop the shell from treating `>` and `<` as redirects.
- `pip freeze` lists **every installed package with its exact version** (`Django==5.2.18`).
- We write `==` exact versions into `requirements.txt`. Unlike Composer, pip has no separate lockfile, so pinning in `requirements.txt` *is* the lock. Everyone (and CI) gets exactly the same versions.
- We only list the packages **we chose**. Their own dependencies (`asgiref`, `sqlparse`) get resolved by pip automatically.
- `requirements-dev.txt` starts with `-r requirements.txt`, meaning "include that file too". One command installs both, like `require` + `require-dev`.

## `pyproject.toml` and ruff

`pyproject.toml` is Python's standard config file for a project, written in **TOML** (an `.ini`-like format). Tools read their own `[tool.<name>]` section, so pytest and ruff both live in it instead of separate config files.

**ruff** is a linter *and* formatter, written in Rust, so it's very fast:
- `ruff check .` is the **linter** (≈ ESLint / PHPStan). `--fix` auto-fixes what it safely can.
- `ruff format .` is the **formatter** (≈ Prettier / PHP-CS-Fixer). It's opinionated: double quotes, 88-character lines, trailing commas.
- Selected rule families: `E`/`W` (pycodestyle style), `F` (pyflakes: unused imports, undefined names), `I` (import sorting), `B` (bugbear: likely bugs), `UP` (pyupgrade: use modern syntax), `DJ` (Django-specific).

When we ran it on the scaffold, the formatter rewrote 5 files, mostly changing `'single'` quotes to `"double"`. In Python both kinds of quote mean exactly the same thing (unlike PHP, where only `"..."` interpolates variables).

## Python basics from Task 2 (`mealcycle/env.py`)

```python
import os                                              # import a whole module, then use os.environ
from django.core.exceptions import ImproperlyConfigured  # import one name out of a module (≈ PHP `use`)

def env_required(name: str) -> str:                    # function with type hints
    value = os.environ.get(name)
    if not value:                                      # no braces: indentation IS the block
        raise ImproperlyConfigured(f"Missing ...: {name}")   # raise ≈ throw; f"..." ≈ "...{$name}"
    return value
```

- **Modules:** every `.py` file is a module, and every folder with an `__init__.py` is a **package**. `from mealcycle.env import env_list` means "file `mealcycle/env.py`, the name `env_list`". There's no autoloader or namespace declaration; the folder path *is* the namespace.
- **Indentation is syntax.** Blocks are defined by 4-space indentation after a `:`. There are no `{}` and no `;`.
- **Type hints** (`name: str -> str`) work like TypeScript annotations, but Python **doesn't enforce them at runtime**. They're for editors and type-checkers.
- **Truthiness:** `if not value:` is true for `None`, `""`, `0`, `[]` and `{}`, like PHP's `empty()`.
- **f-strings:** `f"Hello {name}"` ≈ PHP `"Hello {$name}"` ≈ JS `` `Hello ${name}` ``.
- **List comprehension:** `[item.strip() for item in raw.split(",") if item.strip()]` ≈ `array_filter(array_map(...))`, or JS `.map().filter()`, written as one expression.
- **Docstrings:** the `"""..."""` string right under a `def` documents it (≈ a PHPDoc block). Editors show it on hover.
- **`None`** is Python's `null`. **`True` / `False`** are capitalized.

## pytest basics

- pytest finds files named `test_*.py` and runs every function whose name starts with `test_`.
- `assert x == y` is the whole assertion API. When it fails, pytest prints both sides.
- `with pytest.raises(SomeError, match="text"):` means "the code inside this block must raise SomeError, with a message containing `text`" (≈ PHPUnit `expectException`).
- **Fixtures** are injected **by parameter name**. `def test_x(monkeypatch):` receives pytest's built-in `monkeypatch`, which can set or remove env vars and automatically undoes the change after the test.
- `@pytest.mark.django_db` gives a test database access (pytest-django blocks DB access otherwise, so tests don't hit the DB by accident). Each test's changes are rolled back afterwards.
- pytest-django creates a separate **`test_mealcycle`** database for the run and drops it at the end, so your real data is never touched.

## How settings load env vars now

`load_dotenv(BASE_DIR / ".env")` copies `.env` into `os.environ`, **without overwriting variables that are already set**. That's why `SECRET_KEY= python manage.py check` (an empty value set in the shell) wins over `.env` and triggers our "Missing required environment variable" error.

`BASE_DIR / ".env"`: `BASE_DIR` is a `pathlib.Path`, and `/` joins paths (≈ `base_path('.env')` in Laravel).

`createdb -h localhost -U postgres mealcycle` is a command-line tool that ships with Postgres (≈ `CREATE DATABASE mealcycle;`).

## Classes, inheritance, and `self` (from `accounts/models.py`)

```python
class User(AbstractBaseUser, PermissionsMixin):     # extends TWO parents
    email = models.EmailField(unique=True)          # class attribute = a DB column
    objects = UserManager()                         # the manager: User.objects.create_user(...)

    def __str__(self):                              # ≈ __toString()
        return self.email

    def save(self, *args, **kwargs):                # override a parent method
        self.email = normalize_email_address(self.email)
        super().save(*args, **kwargs)               # ≈ parent::save(...$args)
```

- **`class A(B, C):`**: parent classes go in parentheses. Python allows **multiple inheritance**. A **mixin** like `PermissionsMixin` is a small class meant to be mixed in, much like a **PHP trait**.
- **`self`** ≈ `$this`, but it's **written explicitly** as the first parameter of every method. Python passes it automatically when you call `user.save()`.
- **Attributes use a dot:** `self.email` ≈ `$this->email`. There's no `->` and no `$`.
- **No `new` keyword:** `User(email="a@b.com")` creates an instance.
- **Keyword arguments:** `create_user(email="a@b.com", is_staff=True)` ≈ PHP 8 named arguments.
- **`*args, **kwargs`** collect "any extra positional args" (a tuple) and "any extra named args" (a dict). Passing them on with `super().save(*args, **kwargs)` forwards everything (≈ `...$args`). It's the standard way to override a method without caring about its exact signature.
- **Dunder methods** (double underscore): `__str__`, `__init__` (≈ `__construct`) and so on are hooks Python calls for you. `str(user)` calls `user.__str__()`.
- **`is` vs `==`:** `x is True` checks identity (it's the very same object). `==` checks equality. Use `is` for `None`, `True` and `False`.

## Django models vs Eloquent

| Eloquent | Django |
|---|---|
| Columns defined in a migration you write | **Columns defined on the model**: `email = models.EmailField(unique=True)` |
| `php artisan make:migration` (you write the SQL changes) | `python manage.py makemigrations`: Django **compares models to existing migrations and generates the file** |
| `php artisan migrate` | `python manage.py migrate` |
| `User::create([...])`, `User::where(...)` | `User.objects.create(...)`, `User.objects.filter(...)`. `objects` is the **manager** |
| Custom static methods / query scopes | **Custom manager methods**, like our `create_user` |

So in Django **the model is the source of truth**, and migrations are derived from it. Our first migration (`accounts/migrations/0001_initial.py`) was generated entirely from the `User` class. Migrations are still committed to git and reviewed, the same as in Laravel.

## The custom User model

- `AbstractBaseUser` gives only `password` + `last_login` plus password hashing (`set_password`, `check_password`). `PermissionsMixin` adds `is_superuser`, `groups` and `user_permissions`.
- `USERNAME_FIELD = "email"` tells Django "log in with email". `REQUIRED_FIELDS = []` means `createsuperuser` asks for nothing beyond email + password.
- `AUTH_USER_MODEL = "accounts.User"` in settings makes every part of Django (admin, auth, sessions, third-party packages) use our table. It had to be set **before the first `migrate`**: when we ran it, Postgres got `accounts_user` and **no** `auth_user` table.
- **Unusable password:** `set_unusable_password()` stores a marker starting with `!` that can never match any password. Our `save()` does this whenever no password is set.
- **`get_by_natural_key`** is what Django's login calls to find the user. We normalize the email there so `BOSS@example.com` logs in as `boss@example.com`.

## Decorators (from `accounts/admin.py`)

```python
@admin.register(User)
class UserAdmin(admin.ModelAdmin): ...
```
A decorator is a function that receives the class (or function) below it and can register it, wrap it or change it. `@admin.register(User)` is the same as writing `admin.site.register(User, UserAdmin)` after the class. It looks like a PHP 8 attribute (`#[...]`), but it actually **runs code**, at import time.

**Tuples:** `("email", "is_active")` is a **tuple**, an immutable list. A one-item tuple needs a trailing comma: `("email",)`. Without it, `("email")` is just a string in parentheses.

## A DRF request, end to end (from Task 4)

```
GET /api/v1/health/
  → mealcycle/urls.py   path("api/v1/", include("core.urls"))   ≈ Route::prefix('api/v1')->group(base_path('routes/core.php'))
  → core/urls.py        path("health/", HealthView.as_view())   ≈ Route::get('health', HealthController::class)
  → core/views.py       HealthView.get(self, request)           ≈ HealthController::__invoke(Request $request)
  → Response({...})     DRF turns the dict into JSON           ≈ response()->json([...])
```

- **`APIView`** is a class-based view: **one method per HTTP verb** (`get`, `post`, `put`, `delete`). A verb without a method returns **405** automatically.
- **`.as_view()`** turns the class into the plain function that Django's URL router expects. You always write `SomeView.as_view()` in `urls.py`.
- **Class attributes configure the view:** `permission_classes = [AllowAny]` makes it public, overriding the global `IsAuthenticated` default (≈ removing the `auth` middleware for one route). `authentication_classes = []` means "don't even try to identify the user".
- **Python dicts** `{"status": "ok"}` ≈ PHP associative arrays `['status' => 'ok']`, and DRF serializes them to JSON.
- **`status.HTTP_503_SERVICE_UNAVAILABLE`** is a named constant for 503 (≈ `Response::HTTP_SERVICE_UNAVAILABLE` in Symfony/Laravel).

## `try` / `except`

```python
try:
    connection.ensure_connection()
except OperationalError:              # ≈ catch (OperationalError $e)
    return Response(..., status=503)
```
Python's version of `try/catch`. Use `except SomeError as e:` if you need the exception object. There's also `finally:` like PHP, and `else:`, which runs only if nothing was raised.

## Mocking with `unittest.mock.patch`

```python
with patch("core.views.connection") as mock_connection:
    mock_connection.ensure_connection.side_effect = OperationalError("db down")
    response = api_client.get(HEALTH_URL)
```
- `patch("core.views.connection")` **temporarily replaces** the name `connection` *inside the `core.views` module* with a fake object (a `MagicMock`), and puts it back when the `with` block ends. You patch **where the name is used**, not where it's defined.
- `side_effect = SomeError(...)` makes the fake **raise** that error when it's called (≈ Mockery's `->andThrow()`). `return_value = x` makes it return `x` instead (≈ `->andReturn()`).
- **`with ... as x:`** is a *context manager*: setup on entry, guaranteed cleanup on exit, even if an error happens. It's also used for files (`with open(path) as f:`) and `pytest.raises`.

## Fixtures in `conftest.py`

```python
@pytest.fixture
def api_client():
    return APIClient()
```
Any test that has a parameter named `api_client` receives a new `APIClient`. pytest finds `conftest.py` files automatically, with no import needed. pytest-django also provides built-in fixtures we used: `client`, `admin_client` (already logged in as a superuser) and `admin_user`.

## Unpacking with `*`

```python
"DEFAULT_RENDERER_CLASSES": [
    "rest_framework.renderers.JSONRenderer",
    *(["rest_framework.renderers.BrowsableAPIRenderer"] if DEBUG else []),
],
```
- `x if condition else y` is Python's ternary (≈ `condition ? x : y`).
- `*[...]` **spreads** a list into the surrounding list (≈ JS `...[...]`, PHP `...[...]`). So the list is `[JSON, Browsable]` when `DEBUG` is on, and just `[JSON]` otherwise.

## Request lifecycle: every file a GET request passes through

**At startup (once):**
1. `manage.py` sets `DJANGO_SETTINGS_MODULE = "mealcycle.settings"` (≈ `artisan`).
2. `mealcycle/settings.py` loads `.env`, apps, `MIDDLEWARE`, `ROOT_URLCONF` and `REST_FRAMEWORK`.
3. `mealcycle/wsgi.py` creates `application`, the entry point for every request (≈ `public/index.php`). `runserver` finds it via `WSGI_APPLICATION`, and gunicorn loads it in production.

**Per request (`GET /api/v1/health/`):**
```
① mealcycle/wsgi.py      application receives the HTTP request → Django builds `request`
② MIDDLEWARE              settings.py list, top → bottom (sessions, CSRF, auth, ...)
③ mealcycle/urls.py       "api/v1/" matches → include("core.urls") gets "health/"
④ core/urls.py            "health/" → HealthView.as_view()
⑤ DRF APIView.dispatch()  authentication_classes → permission_classes → picks get()
⑥ core/views.py           HealthView.get() → ensure_connection() → Response({...})
⑦ DRF renderer            dict → JSON (or the browsable HTML page under DEBUG)
⑧ MIDDLEWARE              back up, bottom → top, adding response headers
```

| Step | Django | Laravel |
|---|---|---|
| Entry point | `mealcycle/wsgi.py` | `public/index.php` |
| Global middleware | `MIDDLEWARE` in settings | `Kernel.php` / `bootstrap/app.php` |
| Root routes | `mealcycle/urls.py` | `routes/api.php` |
| Grouped routes | `include("core.urls")` | `Route::prefix()->group()` |
| Per-route auth | `permission_classes` on the view | `->middleware('auth')` on the route |
| Controller | `HealthView.get()` | `HealthController@index` |

Two differences from Laravel:
- **URLs are matched in pieces.** The project urls.py strips its prefix and hands the rest to the app's urls.py.
- **DRF checks auth inside the view** (in `dispatch()`), using class attributes or the `REST_FRAMEWORK` defaults, not with route middleware. That's why `HealthView` sets `AllowAny`: otherwise the global `IsAuthenticated` default returns 403.

## Project package vs apps, and how Django finds them

```
mealcycle/                ← the git repo
└── backend/
    ├── manage.py
    ├── mealcycle/        ← the PROJECT config package (named by `startproject mealcycle`)
    ├── accounts/         ← an APP
    └── core/             ← an APP
```

- **The project package** (`backend/mealcycle/`) is configuration and wiring: `settings.py`, the root `urls.py`, `wsgi.py`/`asgi.py`, our `env.py`. It is **not** in `INSTALLED_APPS`, so it can't have models, migrations or admin. ≈ Laravel's `config/` + `bootstrap/`.
- **Apps** (`accounts/`, `core/`, later `pantry/`, `meals/`) are features. Django only discovers models, migrations, admin and so on in apps listed in `INSTALLED_APPS`.
- **`core`** is for project-wide features that don't belong to one domain (health check now; shared base models or audit logs later). It's an app, so it can grow tables. The config package can't.

**How Django finds the config package:**
1. `python manage.py` puts the script's folder (`backend/`) on `sys.path`, Python's import search path. So `import mealcycle` finds `backend/mealcycle/` (a package, because it has `__init__.py`). This is also why `import accounts` works.
2. `DJANGO_SETTINGS_MODULE = "mealcycle.settings"` is a dotted import path (dots = folders) to the settings file. It's set in `manage.py`, `wsgi.py`, `asgi.py` (each `setdefault`, so a real env var wins) and in `pyproject.toml` for pytest.
3. `settings.py` then names the rest: `ROOT_URLCONF = "mealcycle.urls"`, `WSGI_APPLICATION = "mealcycle.wsgi.application"`.
4. `BASE_DIR = Path(__file__).resolve().parent.parent`. `__file__` (≈ PHP `__FILE__`) is `backend/mealcycle/settings.py`, so two `.parent`s give `backend/`.

Renaming the folder means changing the folder **and** every dotted path that mentions it, together. Changing only one gives `ModuleNotFoundError`.

## Typical layouts

| Layout | Config package | Apps | Seen in |
|---|---|---|---|
| Default | `<project>/` | next to `manage.py` | docs, tutorials (what `startproject` makes) |
| **`config/`** | `config/` | next to `manage.py` | cookiecutter-django, many companies |
| Grouped apps | `config/` | inside `apps/` (or a product-named package) | large codebases with many apps |

Inside every app:
```
app/
├── __init__.py, apps.py
├── models.py          ≈ app/Models
├── migrations/        ≈ database/migrations (but generated)
├── admin.py           ≈ Nova/Filament resources
├── serializers.py     ≈ FormRequest + API Resource
├── views.py           ≈ Controllers
├── urls.py            ≈ a routes/*.php file
├── services.py        ≈ app/Services (optional, business logic)
└── tests/
```

**Biggest difference from Laravel:** Laravel groups by **type** (all models in `app/Models`). Django groups by **feature** (everything pantry-related lives in `pantry/`). When a file grows, turn it into a package: `models.py` → `models/__init__.py` + `models/pantry_item.py`.
