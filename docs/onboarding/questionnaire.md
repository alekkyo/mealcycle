# Onboarding Questionnaire

Sub-project 3. Requirements were gathered during foundation planning. The design comes later.

## Context

MealCycle is AI first. Before it can plan meals, it needs to know what the user is trying to achieve and how much time they have. Following the simplicity principle, this should be as few taps as possible.

## The flow (as described)

1. **Primary goal.** Examples: lose weight, eat healthy, bulk up (more protein). The list may grow.
2. **Sub-goal / approach**, which depends on the goal:
   - *Lose weight:* keto, calorie deficit, paleo, intermittent fasting, …
   - *Eat healthy:* more greens, fewer carbs, …
   - *Bulk up:* high protein, …
3. **Prep availability.** When the user has time to meal prep. The app tells them **roughly how much prep time** they'll need.
4. **Meals per week.** For example, 3 or 6+. This **scales the portions and quantities** of the plan.

## Data model notes

- Onboarding answers live in their own models, **not** on the User model, because they change over time and we may want their history.
- Goals and sub-goals are probably reference data (a table, or a fixed set of choices), so the AI and the app share the same vocabulary.

## Open questions

- Can a user pick more than one goal or sub-goal?
- Is the prep-time estimate computed by rules (meals × average prep time) or by the AI?
- Do we need body stats (weight, height, activity level) for calorie-based goals, or is that too many steps?
- Do we need dietary restrictions and allergies (vegetarian, nut allergy, …)? This seems important for safety.
- What format is "when they have time"? Days of the week, a time of day, or both?
