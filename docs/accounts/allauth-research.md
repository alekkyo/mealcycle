# django-allauth: research notes (2026-10-17)

Facts gathered from the official docs, the changelog, PyPI and the allauth source, before designing the auth sub-project. Facts that still need confirming in code are marked **(verify)**.

## Version and support
- **65.20.0** (released 2026-10-16). Requires Python ≥ 3.11. Supports Django 4.2–6.1, so our 3.13 + 5.2 setup is fine.
- Install: `django-allauth[headless]` (pulls in `pyjwt[crypto]`). Add `[socialaccount]` later for Apple/Google.

## Headless API
- Apps: `allauth`, `allauth.account`, `allauth.headless`. URLs: `path("_allauth/", include("allauth.headless.urls"))`.
- `HEADLESS_ONLY = True` turns off allauth's HTML pages. `HEADLESS_CLIENTS = ("app",)` exposes only the mobile-app API.
- URL shape: `/_allauth/app/v1/...`. Relevant endpoints:

| Endpoint | Purpose |
|---|---|
| `POST auth/signup` | sign up (email only, when passwords are off) |
| `POST auth/email/verify` | confirm the signup email with a code |
| `POST auth/code/request` | request a login code |
| `POST auth/code/confirm` | log in with the code |
| `GET auth/session` / `DELETE auth/session` | current user / log out |
| `POST tokens/refresh` | new JWT pair |
| `POST auth/provider/token` | Apple/Google login (later) |

- Steps that aren't finished come back as **401 with a `flows` list**, telling the app what to do next.

## Passwordless email
- Email-only signup: `ACCOUNT_SIGNUP_FIELDS = ["email*"]` gives the user an unusable password.
- Login methods: `ACCOUNT_LOGIN_METHODS = {"email"}`. Our User has no username, so also `ACCOUNT_USER_MODEL_USERNAME_FIELD = None`.
- Login by code: `ACCOUNT_LOGIN_BY_CODE_ENABLED`, `..._TIMEOUT` (default 180 s), `..._MAX_ATTEMPTS` (3), `..._SUPPORTS_RESEND`.
- Email verification by code: `ACCOUNT_EMAIL_VERIFICATION = "mandatory"`, `ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED`, `..._TIMEOUT` (900 s), `..._MAX_ATTEMPTS` (3).
- **Default code format:** 8 characters, letters and digits, dashed (e.g. `WDJB-MJHT`, changed in 65.15). It's configurable (`ACCOUNT_LOGIN_BY_CODE_FORMAT` / `ALLAUTH_USER_CODE_FORMAT`) **(verify exact setting for 6 digits)**.
- **There's no single "sign up or log in" endpoint.** Signup and login-by-code are separate flows.
- With enumeration protection on (`ACCOUNT_PREVENT_ENUMERATION=True`, the default):
  - `code/request` for an **unknown** email pretends a code is pending and sends an "unknown account" email instead.
  - `signup` for an **existing** email pretends to succeed and sends an "account already exists" email.

## Tokens for the mobile app
- JWT: `HEADLESS_TOKEN_STRATEGY = "allauth.headless.tokens.strategies.jwt.JWTTokenStrategy"`.
- Settings: `HEADLESS_JWT_ALGORITHM` (RS256), `HEADLESS_JWT_PRIVATE_KEY` (a PEM key), `..._ACCESS_TOKEN_EXPIRES_IN` (300 s), `..._REFRESH_TOKEN_EXPIRES_IN` (86400 s = **1 day**), `HEADLESS_JWT_ROTATE_REFRESH_TOKEN` (True).
- The app sends `Authorization: Bearer <access>` and refreshes with `POST /_allauth/app/v1/tokens/refresh {"refresh_token": ...}`.
- DRF integration: `allauth.headless.contrib.rest_framework.authentication.JWTTokenAuthentication`, so our own endpoints (like `/api/v1/me/`) accept the same tokens.

## Our models
- allauth adds an `account_emailaddress` table (verified/primary status per email). `User.email` stays as the primary copy.
- allauth creates users with `user.save()`, not our manager. Our email lowercasing already lives in `User.save()`, so that's fine.
- **Hook for the trial:** the `allauth.account.signals.user_signed_up` signal fires for email *and* later social signups. That's the one place to create `Profile(trial_started_at=now)`.

## Templates
- Login code email: `account/email/login_code_subject.txt` / `login_code_message.txt` (override to brand it). There's no built-in magic link (we chose code-only anyway).

## Rate limits
- Built-in defaults include `request_login_code: 20/m/ip,3/m/key`, `login_failed: 10/m/ip,5/300s/key`, `confirm_email: 1/10s/key`, `signup: 20/m/ip`.
- They use Django's cache, so production with several servers needs a shared cache (Redis). Locally the default in-memory cache is fine.

## Apple/Google later
- Both support the native "provider token" flow (the app sends an `id_token`).
- Linking to an existing email account: `SOCIALACCOUNT_EMAIL_AUTHENTICATION` + `..._AUTO_CONNECT` (both off by default).
- Apple native apps use the bundle ID as `client_id`.

Sources: docs.allauth.org (headless installation/configuration, JWT token strategy, account configuration, rate limits, Apple provider), the allauth OpenAPI spec and source on Codeberg, PyPI.
