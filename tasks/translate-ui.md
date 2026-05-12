# i18n Completeness

Find hardcoded UI strings that should be localized and fix them. **One PR with all fixes.**

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: doc/UI language(s), translation file location, test command, build command, default branch, push protocol. If the dispatcher passed `allowed_tasks` and `translate-ui` is not in it, exit silently.

**Audit scope.** Honor `Audit scope`, `Exclude`, and the **hardcoded baseline exclude** defined in `bundles/_multi-runner.md` → "Optional config fields" (single source of truth — do not inline the list here). Only grep UI templates and components inside `Audit scope` (when set); never edit code or translation files under `Exclude` or the baseline list.

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`), operate inside that app only:
- Detect the i18n setup **under `<app_path>`** first. Most monorepos have per-app translation files (`<app_path>/locales/`, `<app_path>/messages/`, `<app_path>/i18n/`). Fall back to the top-level translation file location only if none exist inside the app.
- Only scan UI components under `<app_path>` for hardcoded strings.
- Only edit translation files under `<app_path>` (or the fallback repo-wide file if that's what the app uses).
- Use the app-scoped test and build commands from the scoped config.
- Branch: `night-shift/i18n-<app-slug>-YYYY-MM-DD`.
- PR title: `night-shift/i18n: <app_path> — localize hardcoded strings`.

Without an `app_path`, behave as before.

## High bar — default is silent
Only open a PR when there are clearly user-visible hardcoded strings that belong in the translation files. Do not touch strings that are intentionally not localized (brand names, error codes, debug-only text). **If the app is broadly localized, exit silently** — a tiny sweep PR is more churn than signal.

## Steps
1. Check for an existing open night-shift i18n PR for this app (or repo when unscoped):
   ```
   gh pr list --search "night-shift/i18n in:title" --state open
   ```
   If one exists for the same app, exit silently — do not stack PRs.
2. Detect the project's i18n setup. Prefer a setup inside `<app_path>` when scoped. Check, by ecosystem:
   - **JS/TS:** `next-intl`, `react-i18next` / `i18next`, `formatjs` / `react-intl`, `vue-i18n`, `svelte-i18n`, or a custom dictionary helper.
   - **PHP — Symfony:** `symfony/translator` (`translations/*.{yaml,xliff,php}`, `trans()` calls in PHP, `{% trans %}` / `|trans` in Twig).
   - **PHP — Laravel:** `Illuminate\Translation` (`lang/` or `resources/lang/`, `__('…')` / `@lang('…')` in Blade, `trans()` / `Lang::get()` in PHP).
   - **PHP — WordPress:** gettext functions (`__()`, `_e()`, `_n()`, `esc_html__()`) backed by `.po` / `.mo` files under `languages/`.
   - **PHP — Drupal:** `t('…')` and `\Drupal::translation()` in PHP/`*.module`/`*.theme`, `{{ '…'|t }}` and `{% trans %}` in Twig, `.po` imports under `translations/`.
   - **Python — Django:** `gettext()` / `_()` / `{% trans %}` in templates, `locale/<lang>/LC_MESSAGES/django.po`.
   - **Python — Flask/Babel:** `flask_babel` / `babel`, `messages.pot` + `translations/<lang>/LC_MESSAGES/`.
   - **Ruby — Rails:** `I18n.t` / `t(…)` in views/controllers, `config/locales/*.yml`.
   - **Other:** any custom dictionary keyed lookup (`messages.<lang>.json`, `locales/<lang>.json`, etc.).

   If there is no i18n setup at all, exit silently — that is a config decision, not a night-shift fix.

3. Grep UI templates and components (under `<app_path>` when scoped) for hardcoded user-visible strings. Match the grep to the template language(s) actually used in the repo:
   - **JSX/TSX:** text nodes inside JSX, `placeholder=`, `aria-label=`, `title=`, `alt=`, `label={"…"}`.
   - **Vue / Svelte SFCs:** text inside `<template>` tags, attribute strings (`:placeholder`, `aria-label`, `title`, `alt`) not bound to a translation call.
   - **Twig** (Symfony/Drupal): text inside `<tag>…</tag>` not wrapped in `{{ … | trans }}` / `{{ … | t }}` / `{% trans %}…{% endtrans %}`; attribute values not piped through `|trans` / `|t`.
   - **Blade** (Laravel): text outside `{{ __('…') }}` / `@lang('…')` / `{!! __('…') !!}` — including HTML attribute values on Blade-rendered tags.
   - **Raw PHP** (WordPress / Drupal `*.module` and `*.theme` / framework-less): `echo`, `print`, `return` of user-visible strings in helpers, rendered widgets, hook implementations.
   - **ERB / HAML** (Rails): text outside `<%= t('…') %>` / `= t('…')`.
   - **Django/Jinja templates:** text outside `{% trans %}` / `{{ _('…') }}` / `{{ gettext('…') }}`.

   Skip dev-only strings, log messages, exception messages with no UI surface, and test files.
4. For **all** components with clear hardcoded text:
   - Extract the strings to the project's translation files using existing key-naming conventions.
   - Add translations for all configured locales (use the source language as a placeholder for missing locales and flag them in the PR body).
   - Replace the hardcoded text with translation calls in the component.
5. Collect all fixes in one branch (include app slug when scoped):
   ```
   # scoped:
   git checkout -b night-shift/i18n-<app-slug>-YYYY-MM-DD
   # unscoped:
   git checkout -b night-shift/i18n-YYYY-MM-DD
   ```
6. Run the scoped **test suite** and the scoped **build command**. Both must pass.
7. Push and open the PR (prefix title with `<app_path> — ` when scoped). The wrapper has already created the standard labels for this repo — just attach them. **Always use `--body-file`, never inline `--body`.** End the body with the Night Shift footer:
   ```
   cat > /tmp/night-shift-pr-body.md <<'EOF'
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

   # Stagger PR creation. Spec: bundles/_multi-runner.md → "PR creation throttle".
   LAST=/tmp/night-shift-pr-last-created
   if [ -f "$LAST" ]; then
     ELAPSED=$(( $(date +%s) - $(cat "$LAST") ))
     [ "$ELAPSED" -lt 90 ] && sleep "$((90 - ELAPSED))"
   fi
   PR_URL=$(gh pr create --title "night-shift/i18n: <app_path> — localize hardcoded strings" \
     --label night-shift \
     --body-file /tmp/night-shift-pr-body.md)
   date +%s > /tmp/night-shift-pr-last-created
   # Post-create ritual — REQUIRED after every gh pr create. Do NOT return to the wrapper without running every line below. Skipping leaves PR bodies flattened (literal \n on GitHub) or auto-merge unarmed. Spec: bundles/_multi-runner.md.
   gh pr edit "$PR_URL" --add-label night-shift
   BODY=$(gh pr view "$PR_URL" --json body -q .body)
   case "$BODY" in *'\n'*) printf '%s' "$BODY" | python3 -c "import sys;sys.stdout.write(sys.stdin.read().replace(chr(92)+chr(110),chr(10)))" > /tmp/night-shift-body-fix.md && gh pr edit "$PR_URL" --body-file /tmp/night-shift-body-fix.md ;; esac
   gh pr merge "$PR_URL" --auto --squash 2>/dev/null || gh pr merge "$PR_URL" --auto || true
   ```

   **Self-review.** After the post-create ritual above, run the **Self-review + one revision** step from `_multi-runner.md` before returning your one-line result. One review, at most one revision commit, same branch; if the revision breaks tests, revert with `git push --force-with-lease` and keep the original PR.

## Idempotency
- One sweep PR open at a time.
- If no hardcoded user-visible strings remain in the configured key pages, exit silently.
