# Task 06 — Accessibility

Audit key pages for WCAG 2.1 AA violations and fix one issue tonight.

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: key pages, test command, build command, push protocol. If task 6 is not in the task list, exit.

## Steps
1. Read the source of each configured **key page** and the components they render.
2. Look for WCAG 2.1 AA issues:
   - Missing or incorrect `alt` text on images
   - Form inputs without associated `<label>`
   - Buttons / links with no accessible name (icon-only without `aria-label`)
   - Color contrast that is clearly insufficient
   - Missing or wrong heading hierarchy
   - Interactive elements that aren't keyboard reachable
   - Missing `lang` attribute on `<html>`
   - `role` / `aria-*` misuse
3. Pick **one** clear violation tonight. Fix it at the component level (so all consumers benefit).
4. If the project has a11y tests, add a test that would have caught the regression. Otherwise add at minimum a snapshot or unit test that exercises the fix.
5. Run the **full test suite** and the **build command**. Both must pass.

## Commit
```
git add -A
git commit -m "nightshift(a11y): fix <short description>"
```
Push using the project's push protocol.

## Idempotency
- One issue per night.
- If no clear violations remain on the configured key pages, exit silently.
