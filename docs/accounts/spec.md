# Accounts & Auth (email login): Design Spec

**Status:** Approved · **Date:** 2026-10-17 · **Sub-project:** 2 (see [product/overview.md](../product/overview.md))

Decisions and their reasoning: [auth.md](auth.md). allauth facts: [allauth-research.md](allauth-research.md).

## Goal

A user signs up or logs in with **only their email and a 6-digit code**, on one email screen and one code screen. The mobile app gets JWT tokens and stays logged in for 90 days. Every new user gets a 14-day trial, visible at `GET /api/v1/me/`.

## Out of scope

Apple/Google login (later sub-project), blocking access after the trial (Billing), onboarding questions, production email provider and Redis (deployment), the mobile app itself.

## 1. User flow

```
Email screen ──► Code screen ──► logged in
```
1. The app calls `POST /_allauth/app/v1/auth/code/request {"email"}`.
   - **Existing account:** a code is emailed, and the response says a code is pending.
   - **Unknown email:** a 400 error (enumeration protection is off). The app then calls `POST /_allauth/app/v1/auth/signup {"email"}`, which emails a verification code.
2. The user types the code (or autofills it from the email subject).
   - Login: `POST /_allauth/app/v1/auth/code/confirm {"code"}`
   - Signup: `POST /_allauth/app/v1/auth/email/verify {"key": code}`
3. The success response contains the tokens: `access_token`, `refresh_token`.
4. The app sends `Authorization: Bearer <access_token>` on every request, and refreshes with `POST /_allauth/app/v1/tokens/refresh {"refresh_token"}`.

Exact request/response shapes come from allauth's OpenAPI spec and are pinned by our tests.

## 2. Package

`django-allauth[headless]`, pinned exactly at install time (65.20.x). It pulls in `pyjwt[crypto]`.

## 3. Settings (`config/settings.py`)

**Apps and middleware**
- `INSTALLED_APPS`: add `"allauth"`, `"allauth.account"`, `"allauth.headless"`. **`"accounts"` must come before the allauth apps**, so our email templates override allauth's (Django uses the first matching template in app order).
- `MIDDLEWARE`: append `"allauth.account.middleware.AccountMiddleware"`.
- `AUTHENTICATION_BACKENDS`: `django.contrib.auth.backends.ModelBackend` (admin login) + `allauth.account.auth_backends.AuthenticationBackend`.

**Accounts (passwordless email)**
```python
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*"]                 # no password field → unusable password
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_PREVENT_ENUMERATION = False                # one-screen UX (see auth.md)
ACCOUNT_EMAIL_SUBJECT_PREFIX = ""                  # subject is exactly our text

ACCOUNT_LOGIN_BY_CODE_ENABLED = True
ACCOUNT_LOGIN_BY_CODE_TIMEOUT = 600                # 10 minutes
ACCOUNT_LOGIN_BY_CODE_MAX_ATTEMPTS = 3

ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED = True
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_TIMEOUT = 600
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_MAX_ATTEMPTS = 3
```
Plus the setting(s) that make both codes **6 numeric digits** (exact name to be confirmed in Task 1).

**Headless + JWT**
```python
HEADLESS_ONLY = True
HEADLESS_CLIENTS = ("app",)
HEADLESS_TOKEN_STRATEGY = "allauth.headless.tokens.strategies.jwt.JWTTokenStrategy"
HEADLESS_JWT_ALGORITHM = "HS256"
HEADLESS_JWT_PRIVATE_KEY = env_required("JWT_SECRET_KEY")
HEADLESS_JWT_ACCESS_TOKEN_EXPIRES_IN = 15 * 60          # 15 minutes
HEADLESS_JWT_REFRESH_TOKEN_EXPIRES_IN = 90 * 24 * 3600  # 90 days
HEADLESS_JWT_ROTATE_REFRESH_TOKEN = True
```
- **HS256 (one shared secret), not RS256 (key pair):** only our own server issues and checks tokens, so a key pair adds nothing. It's one string in `.env`, kept separate from `SECRET_KEY` so it can be rotated (which logs everyone out) independently.

**DRF**: `DEFAULT_AUTHENTICATION_CLASSES` becomes `[allauth…rest_framework.authentication.JWTTokenAuthentication, rest_framework.authentication.SessionAuthentication]`. JWT is for the app; the session keeps the browsable API working while you're logged into the admin.

**Email**
- If `EMAIL_HOST` is set: SMTP backend with `EMAIL_HOST`, `EMAIL_PORT` (default 2525), `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS = True` (Mailtrap locally).
- Otherwise: console backend (the email is printed in the terminal). Tests always use Django's in-memory outbox.
- `DEFAULT_FROM_EMAIL` from env, defaulting to `"MealCycle <no-reply@mealcycle.local>"`.

**`.env.example`** gains `JWT_SECRET_KEY`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`. CI sets a placeholder `JWT_SECRET_KEY`.

## 4. URLs

```
/_allauth/app/v1/...   → include("allauth.headless.urls")   (config/urls.py)
/api/v1/me/            → accounts.views.MeView               (accounts/urls.py, included under api/v1/)
```

## 5. `Profile` model (`accounts/models.py`)

```python
TRIAL_LENGTH = timedelta(days=14)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    trial_started_at = models.DateTimeField(default=timezone.now)

    @property
    def trial_ends_at(self): ...        # trial_started_at + TRIAL_LENGTH
    @property
    def trial_is_active(self): ...      # now < trial_ends_at
```
- **Created by a `post_save` signal on `User` when `created=True`** (`accounts/signals.py`, connected in `AccountsConfig.ready()`).
- **Why `post_save` and not allauth's `user_signed_up`:** it fires for *every* way a user is created (allauth signup, the admin, `createsuperuser`, future Apple/Google). So "every user has a profile" always holds, and the trial starts exactly when the account is created. Admins get a (meaningless) trial too, which is harmless.
- Admin: the `Profile` is shown inline on the user **edit** page (`trial_started_at` editable, so support can extend a trial). It's not shown on "add user", where the signal creates it.
- Migration `accounts/0002_profile.py`.

## 6. `GET /api/v1/me/` (`accounts/views.py`)

`MeView(APIView)` uses the default `IsAuthenticated` and returns:
```json
{"email": "alex@example.com", "trial_ends_at": "2026-10-31T09:00:00Z", "trial_active": true}
```
Built with `MeSerializer` (`accounts/serializers.py`). Without a valid token: 401.

## 7. Email templates (`accounts/templates/account/email/`)

Override both the login-code email and the signup verification-code email (exact template file names to be confirmed in Task 1):
- **Subject:** `Your MealCycle code: 482-913` (allauth groups 6-digit codes with a dash; typing it with or without the dash works)
- **Body:** the grouped code, then `Expires in 10 minutes.` Nothing else.

## 8. Errors

| Situation | Status |
|---|---|
| Wrong code | 400 (tries left) |
| 3 wrong tries / expired | 400. The app requests a new code |
| Rate-limited | 429 (allauth defaults, e.g. 3 code requests/min per email) |
| Invalid email | 400 |
| Expired access token | 401. The app refreshes |
| Expired/rotated refresh token | 400. Back to the email screen |

## 9. Tests

All through the real HTTP endpoints with DRF's `APIClient`. Codes are read from `django.core.mail.outbox`.
1. **New user:** code request → 400 → signup → the email has a 6-digit grouped code in the subject → verify → tokens → `/me` 200 with `trial_active: true` and `trial_ends_at` = creation + 14 days.
2. **Returning user:** code request → email → confirm → tokens. Still exactly one `User` and one `Profile`.
3. A wrong code 3× → the next attempt with the right code also fails (the code is burned).
4. An expired code (time moved forward 11 minutes) → fails.
5. `/me` without a token → 401. With a garbage token → 401.
6. Refresh → a new pair. Reusing the old refresh token → rejected.
7. Rate limit: rapid repeated code requests → 429.
8. **Every user gets a profile:** `User.objects.create_user(...)` and `create_superuser(...)` both create one.
9. The email subject format is exactly `Your MealCycle code: ddd ddd`.
10. The admin user page loads with the profile inline.

## 10. Task 1 is a verification spike

The research flagged details to confirm against the installed allauth before writing the real code:
- the setting for **6-digit numeric codes**
- the **template names** for both code emails
- that `code/request` for an **unknown email returns 400** when `ACCOUNT_PREVENT_ENUMERATION = False`
- that `HEADLESS_JWT_PRIVATE_KEY` accepts a **shared secret with HS256**
- whether allauth needs `django.contrib.sites`

If any of these turns out differently, the plan adapts, and a change to the user-visible flow comes back to you before building.

## 11. Docs

- `docs/learning/`: signals, `OneToOneField`, `@property`, JWT, overriding a library's templates, third-party app settings.
- CLAUDE.md: the new env vars and how to set up Mailtrap.

## Done when

- [ ] With Mailtrap configured, you enter your email via `curl`, the code arrives in the Mailtrap inbox with the subject `Your MealCycle code: ddd ddd`, confirming it returns tokens, and `/me` shows your trial
- [ ] Without Mailtrap, the same flow prints the email in the `runserver` terminal
- [ ] All tests pass locally and in CI, and ruff is clean
- [ ] The admin shows each user's trial start
