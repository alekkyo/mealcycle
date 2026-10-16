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
