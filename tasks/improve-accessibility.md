# Accessibility

Audit key pages for WCAG 2.1 AA violations and fix one issue tonight.

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: key pages, test command, build command, push protocol. If this task is not in the task list, exit.

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`), operate inside that app only:
- Read `key pages` from the scoped config (the `apps[]` entry for this app), not the top-level list.
- Only audit and modify files under `<app_path>`.
- Use the app-scoped test and build commands from the scoped config.
- Commit message names the app: `nightshift(a11y): <app_path> — fix <short description>`.

Without an `app_path`, behave as before.

## Steps
1. Read the source of each configured **key page** (scoped to `<app_path>` when set) and the components they render.
2. Look for WCAG 2.1 AA issues:
   - Missing or incorrect `alt` text on images
   - Form inputs without associated `<label>`
   - Buttons / links with no accessible name (icon-only without `aria-label`)
   - Color contrast that is clearly insufficient
   - Missing or wrong heading hierarchy
   - Interactive elements that aren't keyboard reachable
   - Missing `lang` attribute on `<html>`
   - `role` / `aria-*` misuse
3. Pick **one** clear violation tonight. Fix it at the component level (so all consumers benefit). When scoped, the component must live under `<app_path>`.
4. If the project has a11y tests, add a test that would have caught the regression. Otherwise add at minimum a snapshot or unit test that exercises the fix.
5. Run the scoped **test suite** and the scoped **build command**. Both must pass.

## Commit
```
# scoped:
git commit -m "nightshift(a11y): <app_path> — fix <short description>"
# unscoped:
git commit -m "nightshift(a11y): fix <short description>"
```
Push using the project's push protocol.

## Idempotency
- One issue per night.
- If no clear violations remain on the configured key pages, exit silently.
