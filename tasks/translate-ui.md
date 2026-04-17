# i18n Completeness

Find hardcoded UI strings that should be localized and fix them. **One PR with all fixes.**

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: doc/UI language(s), translation file location, test command, build command, default branch, push protocol. If the dispatcher passed `allowed_tasks` and `translate-ui` is not in it, exit silently.

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`), operate inside that app only:
- Detect the i18n setup **under `<app_path>`** first. Most monorepos have per-app translation files (`<app_path>/locales/`, `<app_path>/messages/`, `<app_path>/i18n/`). Fall back to the top-level translation file location only if none exist inside the app.
- Only scan UI components under `<app_path>` for hardcoded strings.
- Only edit translation files under `<app_path>` (or the fallback repo-wide file if that's what the app uses).
- Use the app-scoped test and build commands from the scoped config.
- Branch: `nightshift/i18n-<app-slug>-YYYY-MM-DD`.
- PR title: `nightshift/i18n: <app_path> — localize hardcoded strings`.

Without an `app_path`, behave as before.

## High bar — default is silent
Only open a PR when there are clearly user-visible hardcoded strings that belong in the translation files. Do not touch strings that are intentionally not localized (brand names, error codes, debug-only text). **If the app is broadly localized, exit silently** — a tiny sweep PR is more churn than signal.

## Steps
1. Check for an existing open night-shift i18n PR for this app (or repo when unscoped):
   ```
   gh pr list --search "nightshift/i18n in:title" --state open
   ```
   If one exists for the same app, exit silently — do not stack PRs.
2. Detect the project's i18n setup (e.g. `next-intl`, `react-i18next`, `formatjs`, custom). Prefer an i18n setup inside `<app_path>` when scoped. If there is no i18n setup at all, exit silently — that is a config decision, not a night-shift fix.
3. Grep UI components (under `<app_path>` when scoped) for hardcoded user-visible strings: text inside JSX, `placeholder=`, `aria-label=`, `title=`, `alt=`. Skip dev-only strings, log messages, and test files.
4. For **all** components with clear hardcoded text:
   - Extract the strings to the project's translation files using existing key-naming conventions.
   - Add translations for all configured locales (use the source language as a placeholder for missing locales and flag them in the PR body).
   - Replace the hardcoded text with translation calls in the component.
5. Collect all fixes in one branch (include app slug when scoped):
   ```
   # scoped:
   git checkout -b nightshift/i18n-<app-slug>-YYYY-MM-DD
   # unscoped:
   git checkout -b nightshift/i18n-YYYY-MM-DD
   ```
6. Run the scoped **test suite** and the scoped **build command**. Both must pass.
7. Push and open the PR (prefix title with `<app_path> — ` when scoped). Ensure the standard labels exist first (idempotent), then attach them. End the body with the Night Shift footer:
   ```
   gh label create nightshift --color "0e8a16" --description "Automated by Night Shift" 2>/dev/null || true
   gh label create "nightshift:code-fixes" --color "1d76db" --description "Night Shift code-fixes bundle" 2>/dev/null || true
   gh pr create --title "nightshift/i18n: <app_path> — localize hardcoded strings" \
     --label nightshift --label "nightshift:code-fixes" \
     --body "$(cat <<'EOF'
   ## Plain summary
   <1-2 sentences in English (PR review is always in English, regardless of the product's user language). Which screens / labels / messages now appear in the user's language instead of English (or whichever fallback was leaking through), and which user group benefits most. Skip framework / key-naming jargon. See bundles/_multi-runner.md → "Body header — Plain summary".>

   ## Summary
   Found and localized hardcoded UI strings across <N> components.

   ## Changes
   - <bullet per component, listing extracted strings>

   ## Missing translations
   - <list any locales where placeholder text was used>

   ## Verification
   - <how to confirm strings render correctly>

   ---
   _Run by Night Shift • code-fixes/translate-ui_
   EOF
   )"
   ```

   **Do not** modify `docs/NIGHTSHIFT-HISTORY.md` from this branch — the multi-runner wrapper appends the history row on `main` after you return your one-line result.

## Idempotency
- One sweep PR open at a time.
- If no hardcoded user-visible strings remain in the configured key pages, exit silently.
