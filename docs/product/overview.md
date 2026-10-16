# Product Overview

## Context

MealCycle is an **AI-first meal prep planner and pantry organizer**. It's a real product that will launch to paying users, not a prototype.

## Principles

1. **Simplicity above everything.** Fewer steps is better. Every flow (signup, onboarding, planning) should ask for as little as possible and use sensible defaults. If a design adds a screen or a required field, it has to justify it.
2. **Production quality from day one.** Secrets stay out of git, auth is secure, every feature has tests, and payments are handled reliably.

## Business rules

- New users get a **14-day free trial** when they sign up. It's tracked with `trial_started_at` on the user profile.
- After the trial ends, a **Stripe subscription** is required to keep using the app.

## Platform

- **Mobile app first** (frontend comes later; it's probably React Native / Expo). Web may come later.
- The backend is a Django REST API that the app talks to.

## Backend roadmap

Each sub-project gets its own design → plan → PR cycle.

| # | Sub-project | Summary |
|---|---|---|
| 1 | **Foundation** | Settings from `.env`, Postgres, custom User model, DRF, tests, linting, health check |
| 2 | **Accounts & Auth** | Passwordless email login, Apple/Google login, JWT, trial tracking |
| 3 | **Onboarding** | Goal → sub-goal → prep schedule → meals per week |
| 4 | **Pantry** | What the user has at home |
| 5 | **Recipes & Meal Plans** | The core meal prep data |
| 6 | **AI Suggestions** | Claude generates plans and recipes from goals and the pantry |
| 7 | **Billing** | Stripe subscriptions; access is blocked when the trial ends |

Sub-projects 2 and 3 may be built together, since onboarding happens right after signup.

## Open questions

- Core loop: is it pantry-first, plan-first, or the full cycle (plan → shopping list → pantry → cook → next plan)? The name "MealCycle" suggests the full cycle.
- Does the pantry track quantities ("500g rice") or just have / don't have?
