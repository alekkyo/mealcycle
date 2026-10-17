# Accounts & Auth

Sub-project 2. Requirements were gathered during foundation planning. The design comes later.

## Context

The guiding principle is simplicity: the fewest possible steps to get in. The app is **mobile first**.

## Decisions so far

### No passwords for end users
Users never create or remember a password. They log in by:
1. **Email confirmation (passwordless):** they enter their email, we send an email, and they confirm.
2. **Sign in with Apple**
3. **Sign in with Google**

### The email contains a 6-digit code and a magic link
- On mobile, magic links on their own are unreliable. Tapping the link can open Safari instead of the app, and they fail when the email is opened on a different device from the one logging in.
- A **6-digit code** works everywhere. The **link** is still a one-tap shortcut when it opens on the right device.
- (Proposed, based on the mobile-first decision. We'll confirm it in the auth design.)

### Apple login is required, not optional
Apple's App Store rules require "Sign in with Apple" in any iOS app that offers another third-party login, such as Google.

### One person = one account
A user might sign in with an email code one day and with Apple the next. Both should resolve to the same account, matched by email. Social logins are stored in their own table, linked to the user.

### Scope: email login first, Apple/Google much later (2026-10-17)
- This sub-project builds **email login only** (code + link, tokens for the mobile app, `/me`).
- **Sign in with Apple / Google is postponed to a later sub-project, well after onboarding.** Reminder: Apple requires Sign in with Apple in the iOS app *if* Google login is offered, so the two ship together before App Store submission.
- **Why:** email login works on its own with no third-party developer accounts, and it can be tested end to end with `curl` right away.

### The 14-day trial starts when the account is created (2026-10-17)
- The moment someone first verifies their email, we create the account **and** a `Profile` with `trial_started_at = now`.
- This sub-project includes the `Profile` model and a small "is the trial active?" check. **Blocking access** after the trial stays in the Billing sub-project (with Stripe).
- **Why:** it's the simplest rule ("14 days from signup") and can't be gamed. Starting at onboarding completion or first plan would add a "trial not started" state that every feature has to handle.

### Email: Mailtrap for local development, production provider decided at deployment (2026-10-17)
- Code sends email through Django's email layer (`django.core.mail`, ≈ Laravel's `Mail`), so the provider is only configuration.
- **Local:** Mailtrap's testing inbox over SMTP. Emails are caught in Mailtrap's web inbox and never reach real people. Credentials go in `backend/.env` (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`).
- **No email config set** (e.g. CI, a fresh clone): fall back to the console backend, which prints the email in the terminal.
- **Tests:** Django automatically swaps in an in-memory backend (`mail.outbox`), so tests never send anything.
- **Production:** choose a provider when we deploy (Postmark / Resend / SES); it's a settings + API key change.

## Open questions

- JWT details: token lifetimes and refresh strategy for a mobile app.
- How long codes and links stay valid, rate limiting, and protection against abuse.
- Production email provider (Postmark, Resend, SES, …): decided at deployment.
- Apple's "Hide My Email" relay addresses: how do we match those to an existing account?
