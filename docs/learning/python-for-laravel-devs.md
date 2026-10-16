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
