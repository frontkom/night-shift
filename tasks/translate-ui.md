# i18n Completeness

Find hardcoded UI strings that should be localized and fix them.

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: doc/UI language(s), translation file location, test command, build command, push protocol. If this task is not in the task list, exit.

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`), operate inside that app only:
- Detect the i18n setup **under `<app_path>`** first. Most monorepos have per-app translation files (`<app_path>/locales/`, `<app_path>/messages/`, `<app_path>/i18n/`). Fall back to the top-level translation file location only if none exist inside the app.
- Only scan UI components under `<app_path>` for hardcoded strings.
- Only edit translation files under `<app_path>` (or the fallback repo-wide file if that's what the app uses).
- Use the app-scoped test and build commands from the scoped config.
- Commit message names the app: `nightshift(i18n): <app_path> — localize <component>`.

Without an `app_path`, behave as before.

## Steps
1. Detect the project's i18n setup (e.g. `next-intl`, `react-i18next`, `formatjs`, custom). Prefer an i18n setup inside `<app_path>` when scoped. If there is no i18n setup at all, exit silently — that is a config decision, not a night-shift fix.
2. Grep UI components (under `<app_path>` when scoped) for hardcoded user-visible strings: text inside JSX, `placeholder=`, `aria-label=`, `title=`, `alt=`. Skip dev-only strings, log messages, and test files.
3. Pick **one** component or screen tonight with clear hardcoded text.
4. Extract the strings to the project's translation files using existing key-naming conventions. Add translations for all configured locales (use the source language as a placeholder for missing locales and flag them in the commit body).
5. Replace the hardcoded text with translation calls in the component.
6. Run the scoped **test suite** and the scoped **build command**. Both must pass.

## Commit
```
# scoped:
git commit -m "nightshift(i18n): <app_path> — localize <component>"
# unscoped:
git commit -m "nightshift(i18n): localize <component>"
```
Push using the project's push protocol.

## Idempotency
- One component per night.
- If no hardcoded user-visible strings remain in the configured key pages, exit silently.
