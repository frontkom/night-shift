# Task 07 — i18n Completeness

Find hardcoded UI strings that should be localized and fix them.

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: doc/UI language(s), translation file location, test command, build command, push protocol. If task 7 is not in the task list, exit.

## Steps
1. Detect the project's i18n setup (e.g. `next-intl`, `react-i18next`, `formatjs`, custom). If there is no i18n setup at all, exit silently — that is a config decision, not a night-shift fix.
2. Grep UI components for hardcoded user-visible strings: text inside JSX, `placeholder=`, `aria-label=`, `title=`, `alt=`. Skip dev-only strings, log messages, and test files.
3. Pick **one** component or screen tonight with clear hardcoded text.
4. Extract the strings to the project's translation files using existing key-naming conventions. Add translations for all configured locales (use the source language as a placeholder for missing locales and flag them in the commit body).
5. Replace the hardcoded text with translation calls in the component.
6. Run the **full test suite** and the **build command**. Both must pass.

## Commit
```
git add -A
git commit -m "nightshift(i18n): localize <component>"
```
Push using the project's push protocol.

## Idempotency
- One component per night.
- If no hardcoded user-visible strings remain in the configured key pages, exit silently.
