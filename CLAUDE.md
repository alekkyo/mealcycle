# MealCycle

AI-powered meal prep planner and pantry organizer.

## Project Structure

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

## Backend Stack

- **Framework**: Django 5 + Django REST Framework
- **Database**: PostgreSQL
- **Auth**: Django built-in auth + JWT (to be added)
- **AI**: Anthropic Claude API for meal suggestions
- **Payments**: Stripe (subscription billing)

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

## Django Conventions

- Apps live in `backend/` alongside `manage.py`
- Models use snake_case field names
- Serializers in `serializers.py` per app
- Views in `views.py` per app, using DRF class-based views
- URLs registered in each app's `urls.py`, included in `mealcycle/urls.py`
- Migrations committed to the repo

## Workflow

- All changes go on a new branch off main — never commit directly to main
- Before implementing any feature, write a plan and wait for confirmation
- After implementing, open a PR with a clear description of what changed, why, and how to test it
- Write tests for every feature (happy path + failure cases)
- Run linting before opening a PR
- Only touch files relevant to the current task — do not refactor unrelated code
- If requirements are ambiguous, ask before assuming

## Business Logic

- Users get a 14-day free trial on signup
- After trial, subscription required (Stripe) to continue
- Trial status tracked via `trial_started_at` on the user profile
