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

### The email contains a code only, no magic link (revised 2026-10-17)
*Originally proposed: code + link. Revised after weighing the two.*
- **Code only.** We keep allauth's code strength at **6 digits (or stronger)**, never shorter.
- **Why not a magic link:**
  - **Wrong device:** a link opened on a laptop logs in the laptop's browser, not the phone app.
  - **Email security scanners** (Outlook Safe Links, Defender, Mimecast) "click" every link and use up single-use links before the user does ("link expired").
  - **It needs universal links** (an owned domain + `apple-app-site-association`) to open the app, and in-app browsers still sometimes open a web page.
  - It trains users to click login links in emails, which is what phishing relies on.
- **Why a code is enough:** iOS 17+ and Android autofill one-time codes from Mail above the keyboard, which is one tap, like a link, without leaving the app. It works across devices, and scanners can't consume it.
- **Why not shorter (e.g. 2 digits):** the code length *is* the security. 2 digits = 100 possibilities. With 3 guesses per code and new codes on request, an attacker gets in ≈45% of the time within a day. With 6 digits it's ≈0.006%.
- Magic links: **not planned**. Revisit only if we ship a web app.

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

### Implementation: `django-allauth` in headless mode (2026-10-17)
- **Chosen:** django-allauth's headless API (a JSON API for the mobile app), configured for passwordless email login by code.
- **Why:** Apple + Google login are definitely coming. allauth already handles them, including linking a social login to an existing email account, Apple relay emails and ID-token verification. It's battle-tested security code (codes, expiry, attempt limits, rate limits, enumeration protection).
- **Scaling:** no meaningful difference from a custom build. Both use stateless JWT checks, the extra tables are small and only touched at login, and rate limiting needs a shared cache (Redis) with multiple servers either way.
- **Trade-off:** its API shape (`/_allauth/app/v1/...`) and models come with it.
- **Rejected:** a custom flow + simplejwt. Kept as a reading reference in [approach-1-custom-flow.md](approach-1-custom-flow.md).
- The user chose this for the product, not for learning: *"I want to choose what makes more sense for my app and not for my learning."*

### One email screen; enumeration protection off (2026-10-17)
- The user sees only **email → code**, whether they're new or returning. The app requests a login code, and if the account doesn't exist, it starts signup instead.
- `ACCOUNT_PREVENT_ENUMERATION = False`. Anyone can find out whether an email has an account. Accepted: it's low-sensitivity for a meal-prep app, rate limits stop bulk checks, and it removes a "Sign up vs Log in" choice.
- **Account takeover protection stays strict** (6-digit code, attempt limits, rate limits). Accounts still hold personal data (email, diet/health goals) and control the subscription.

### 6-digit code, made easy to remember (2026-10-17)
- **6 digits**, not 4. Resetting the code doesn't help, because each guess has the same odds against a new random code. A script would guess a 4-digit code in about a week, versus years for 6 digits.
- To address the user's concern about remembering the code while switching apps:
  1. The code goes in the **email subject** ("Your MealCycle code: 482 913"), so it's readable in the notification banner without leaving the app.
  2. **Autofill** (iOS/Android one-time-code suggestions) works for numeric codes.
  3. The code is shown **grouped** (`482 913`).
- **Rejected:** 4 digits + a daily failed-guess cap (a few % yearly takeover risk for a targeted account, and an attacker could lock real users out).
- **What an account takeover would expose** (why this matters): the email address; diet, health and allergy info; the prep schedule (when someone's home); control of the subscription (cancel/change, but card details stay at Stripe); deleting the account and its data; and AI usage billed to us. Health-related data has extra legal weight (GDPR "special category" if we store body stats or medical diets).

### Rate limit: 30 code requests per email per day (2026-10-17, final review)
- allauth's default (3/minute per email) lets slow guessing go on for weeks, which is too much for 6-digit codes. We cap it at **30 per email per day**, plus 20/minute per IP. The worst case is ~3% per year for an attacker targeting one account daily, and that victim would be getting 30 code emails a day.
- **allauth 65.20 bug:** all per-email windows share one cache key, so `"3/m/key,30/d/key"` silently disables the daily window. We use one per-email window only. Revisit when allauth fixes it (then add back a per-minute burst limit).

## Open questions

- JWT details: token lifetimes and refresh strategy for a mobile app.
- How long codes and links stay valid, rate limiting, and protection against abuse.
- Production email provider (Postmark, Resend, SES, …): decided at deployment.
- Apple's "Hide My Email" relay addresses: how do we match those to an existing account?
