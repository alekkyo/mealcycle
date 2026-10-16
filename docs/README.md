# MealCycle Docs

Context, discussions, and decisions for MealCycle, grouped by domain. Each doc records **what we decided, why, and what's still open**, so anyone (including future us) can see how we got here.

| Domain | Doc | Status |
|---|---|---|
| Product | [product/overview.md](product/overview.md) | Vision, principles, roadmap |
| Foundation | [foundation/decisions.md](foundation/decisions.md) | Designing |
| Accounts & Auth | [accounts/auth.md](accounts/auth.md) | Requirements gathered |
| Onboarding | [onboarding/questionnaire.md](onboarding/questionnaire.md) | Requirements gathered |
| Learning | [learning/python-for-laravel-devs.md](learning/python-for-laravel-devs.md) | Python notes for a Laravel developer |

## Conventions

- One folder per domain. Add a new folder when a new domain comes up (e.g. `pantry/`, `billing/`).
- Each doc has these sections: **Context** → **Decisions** (with the reasoning) → **Open questions**.
- When a decision changes, update the doc and note what changed and why. Don't silently overwrite it.
- Detailed specs and implementation plans for a sub-project go in that domain's folder.
