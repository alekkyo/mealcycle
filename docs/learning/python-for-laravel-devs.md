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
