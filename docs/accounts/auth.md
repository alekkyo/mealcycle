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

## Open questions

- JWT details: token lifetimes and refresh strategy for a mobile app.
- How long codes and links stay valid, rate limiting, and protection against abuse.
- Which email provider sends the emails (Postmark, Resend, SES, …)?
- Apple's "Hide My Email" relay addresses: how do we match those to an existing account?
- When does the 14-day trial start: at first login, or when onboarding is complete?
