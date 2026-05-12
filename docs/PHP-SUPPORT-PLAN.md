# PHP support — PLAN

Make Night Shift work as well on PHP repos (Laravel, Symfony, WordPress, Drupal, raw PHP libraries) as it does today on JS/TS. The headline result from three live runs is that **PHP already works substantially better than expected**: the routine sandbox ships with PHP and composer, the audit tasks generalise without modification, and most "JS-bias" we worried about turned out to be over-specific *examples* the model routes around rather than hard blockers.

The plan therefore favours **polyglot prompt edits to the existing tasks** over per-stack bundles. Per the user's direction: tasks that work across multiple stacks > parallel per-stack tasks. There is one exception (a generic config field for audit scope, motivated by Drupal's contrib/custom split) and two optional new tasks that are generic from day one, not PHP-specific.

## Live runs — results

Three routines were spawned to ground-truth this plan instead of relying on static analysis. All have `cron: 0 0 1 1 *` (Jan 1 2027) so they will not auto-fire; **delete from https://claude.ai/code/routines after reviewing**.

| Routine | ID | Target | Shape |
|---|---|---|---|
| `nightshift-php-test-monolog` | `trig_019ZGAA7RivfqBhM3RFGi5di` | `perandre/monolog` (public) | PHP library, phpunit, no DB |
| `nightshift-php-test-symfony-demo` | `trig_01PWvqPYFAYdWdQMg9FfwzTa` | `perandre/symfony-demo` (public) | Full Symfony app, Doctrine ORM, SQLite |
| `nightshift-php-test-drupal-fagskolen` | `trig_01Bunt3C4b4ZbVZNx8CiNBiC` | `perandre/fagskolen-viken` (**private** mirror of `frontkom/fagskolen-viken`) | Production Drupal CMS, contrib + custom modules, Twig themes, Norwegian site |

### Run A — `perandre/monolog` (library) — session `015PDVYvjeYnPedjfmPq84kf`

5 PRs in ~16 minutes. Bundle ran end-to-end. Notable:

| PR | Task | Result |
|---|---|---|
| #1 +6/-0 | update-changelog | Three real entries for #2015 / #2020 / #2022 added under unreleased section |
| #2 +7/-3 | update-user-guide | Handler/formatter reference doc updated for 4 recent feature additions |
| #3 +15/-0 | suggest-improvements | Two concrete improvement ideas, no code change |
| #4 +186/-0 | add-tests | 12 tests added for HtmlFormatter / DeduplicationHandler / RotatingFileHandler; **full suite of 1173 tests / 2142 assertions ran and passed locally** |
| #5 +46/-1 | find-bugs | **Real PHP constructor-order bug** in RotatingFileHandler: `$this->timezone` was assigned *after* `setFilenameFormat()` and `getNextRotation()` had already read it. Surgical fix + 2 regression tests; full handler suite (48 tests) green. |

Silent self-skips that look correct: improve-accessibility (library, no HTML), improve-seo (library), improve-performance (library), translate-ui (library), find-security-issues (no real vulns — correct silence), build-planned-features (no plan files), work-on-issues / work-on-jira-issues (no labelled issues), document-decisions (nothing decision-shaped in recent commits), triage-ci-failures (no Night Shift PRs with red CI yet).

### Run B — `perandre/symfony-demo` (app + DB) — session `01X4nEEwDRan3JJQBQpY2TwP`

5 PRs in ~17 minutes. Bundle ran end-to-end. Notable:

| PR | Task | Result |
|---|---|---|
| #1 +34/-0 | suggest-improvements | Three ideas across the app |
| #2 +335/-0 | add-tests | 10 tests for SecurityController / DeleteUserCommand / PostVoter / RedirectToPreferredLocaleSubscriber / PostRepository; tests pass |
| #3 +10/-7 | improve-accessibility | WCAG 2.1 AA sweep against Twig templates |
| #4 +21/-0 | improve-seo | meta description + Open Graph in `templates/base.html.twig` and `templates/blog/post_show.html.twig`; **correctly classified `/en/admin/` and `/en/login` as auth-only and added them to `robots.txt`** despite the task prompt only enumerating Next.js auth markers |
| #5 +4/-1 | improve-performance | **Doctrine N+1 in `PostRepository::findBySearchQuery()`** — added `addSelect('a','t')` + joins, matching the proven pattern already used by `findLatest()` in the same class. All 53 tests pass. |

Silent self-skips: translate-ui (ambiguous — see open question below), find-bugs (no clear bug), find-security-issues (correct), update-changelog / update-user-guide / document-decisions (demo repo, no recent material), build-planned-features / work-on-issues (no triggers), triage-ci-failures (no NS PRs with red CI).

### Run C — `perandre/fagskolen-viken` (Drupal, private) — session `_(filled in after run)`

_(Currently running. Findings will be appended below.)_

#### Findings — fagskolen-viken (Drupal)

- **Toolchain probe result:** _(paste from routine output)_
- **Per task outcome:** _(table)_
- **Custom vs. contrib bias:** _(did tasks correctly stay out of web/modules/contrib, web/core, vendor?)_
- **Drupal-shape observations:** _(metatag detection, t() / |t i18n, EntityQuery / hook_preprocess patterns)_
- **PRs opened:** `gh pr list --label night-shift -R perandre/fagskolen-viken --state all`
- **Notable observations:** _(free text)_

## Key takeaways from runs A + B

1. **PHP and composer are in the routine sandbox.** `add-tests` ran the full PHPUnit suites against both repos with zero toolchain setup. The "what if PHP isn't available" branch of the plan can be dropped — routine backend is viable for PHP today.

2. **The audit tasks generalise without modification.** find-bugs caught a constructor-order bug in idiomatic PHP that no JS-trained prompt would lead toward. improve-performance caught a Doctrine N+1. improve-seo correctly classified Symfony admin routes. The prompts' JS-flavored *examples* did not constrain the model.

3. **The one likely over-specificity is `translate-ui`.** Both library and app routines were silent here — for the library this is correct, for the app it is ambiguous between "i18n is already complete" and "the JS-only detection list missed `symfony/translator`". The Drupal run resolves this: Drupal's `t()` / `|t` pattern is distinct enough that a silent skip on the Drupal test will confirm the gap.

4. **Routine model wins for PHP today.** Doc + audit tasks need no toolchain beyond what's already in the sandbox. `add-tests` only needs PHP/composer/PHPUnit, which the sandbox supplies. GitHub Actions backend is still a reasonable alternative for teams that want explicit toolchain control, but it is not *required* by the language.

## The plan

Three buckets, in priority order. Bucket 1 is the only one that's load-bearing for "PHP works"; buckets 2 and 3 are polish.

### Bucket 1 — Polyglot prompt edits (single PR, no new tasks)

Every change here keeps the framework's one-task-per-purpose shape. Only the *example lists* grow to cover multiple stacks. No new files; no new bundles.

| File | Edit |
|---|---|
| `bundles/_multi-runner.md:455-456` | Extend the default test-command search to include `composer test`, `vendor/bin/phpunit`, `vendor/bin/simple-phpunit`, `php artisan test`, `vendor/bin/pest`. Extend build-command to include `composer install --no-dev --no-progress`, `php bin/console assets:install`, `php artisan optimize`. Closes the "PHP repo without `CLAUDE.md` silently skips test-needing tasks" gap. |
| `tasks/translate-ui.md:27` | Replace the JS-only detection enumeration (`next-intl`, `react-i18next`, `formatjs`, `custom`) with a polyglot list grouped by ecosystem (JS: as today + `vue-i18n`; PHP: `symfony/translator`, Laravel `Illuminate\Translation`, WordPress gettext, Drupal `t()` / `\|t`; Python: Django gettext; Ruby: Rails I18n). |
| `tasks/translate-ui.md:28` | Generalise the string-grep beyond JSX: add Twig (text inside `<tag>…</tag>` not wrapped in `{{ … \| trans }}` / `{% trans %}…{% endtrans %}`; attribute values not wrapped in `\| trans`), Blade (text outside `{{ __('…') }}` / `@lang('…')`), and raw PHP (echo / return strings from user-facing helpers). |
| `tasks/find-security-issues.md:30-31` | Add PHP-flavored XSS markers next to `dangerouslySetInnerHTML`: `{!! $var !!}` (Blade raw), `{{ var \| raw }}` (Twig raw), `echo $_GET[…]` without `htmlspecialchars()`. The existing "raw SQL string building" line is already universal — leave it. |
| `tasks/improve-seo.md:28-31` | Add Symfony (`#[IsGranted]`, `config/packages/security.yaml` access_control), Laravel (`Route::middleware('auth')`, `$this->middleware('auth')` in controller `__construct`), WordPress (`wp-admin/`, `is_user_logged_in()`), and Drupal (`_role: 'authenticated user'` in route YAML) auth markers next to the Next.js ones. |
| `tasks/improve-performance.md:26-33` | Restructure the bulleted audit areas into stack-agnostic buckets: **Always-on** (N+1, missing indexes, missing caches, blocking I/O — already mostly there); **Frontend-heavy** (bundle size, image sizing, fonts, render-blocking — current JS list); **Backend runtime** (opcache config, eager ORM loading, unbounded query result sets); **DB** (covering indexes, full-table scans, missing LIMIT on listing routes). Move `next/image` and `font-display` into the frontend bucket explicitly. |
| `tasks/improve-accessibility.md:65` | Drop the JS-only test-lib examples (`jest-axe`, `@axe-core/react`). The concept is universal — just say "the project's a11y test framework, if any". Add a one-liner that the audit applies to JSX, Twig, Blade, and plain HTML templates. |
| `skills/night-shift/SKILL.md` | Bump `NIGHT_SHIFT_VERSION` per `CLAUDE.md` workflow rule (frontmatter + HTML comment line). |

**Estimated scope:** 2-3 hours of careful prompt editing. Single PR. Lifts signal on JS repos too (the prompts get cleaner regardless of stack).

### Bucket 2 — Generic config: `Audit scope` and `Exclude`

Production CMSes (Drupal especially, but also any large PHP/Rails/JS app with vendored code) have a recurring problem Night Shift's tasks don't model today: **most of the code in the repo is vendored** and audit PRs against it get rejected on sight. Drupal puts contrib modules under `web/modules/contrib/`, Drupal core under `web/core/`, libraries under `vendor/`. WordPress puts plugins under `wp-content/plugins/` (some custom, most vendored). JS apps put deps under `node_modules/` and sometimes also `vendor/` for monorepo internal packages.

Today the framework relies on the model to figure this out from context. That works for `vendor/` and `node_modules/` reliably; it works less reliably for ecosystem-specific layouts.

**Proposed addition** (to `Night Shift Config` in `CLAUDE.md`, optional):

```markdown
## Night Shift Config
- Audit scope: web/modules/custom, web/themes/custom, src/
- Exclude:     web/modules/contrib, web/core, vendor, node_modules
```

Tasks consult `Audit scope` (if set) as their allowlist for code reads/writes, and always honor `Exclude` regardless. Default if unset: `[. ]` minus the hard-coded list `[vendor, node_modules, .git, dist, build, .next]`.

**Why this is generic, not Drupal-specific:** the same fields help a Rails app exclude `vendor/bundle/`, a Go monorepo exclude `internal/third_party/`, a Next.js monorepo exclude a `packages/legacy-bundle/`. Drupal is just the most painful case because the vendored surface dominates the repo.

**Critical files:**
- `bundles/_multi-runner.md` — add the fields to the Night Shift Config schema description (in the existing `## Defaults when no config exists` table or near it).
- `HOW-TO.md` — document the new fields in "Configure a project".
- Every task that does codebase reads (`find-bugs`, `find-security-issues`, `improve-performance`, `improve-accessibility`, `add-tests`, `translate-ui`, `improve-seo`) — add one line at the top: "Honor `Audit scope` and `Exclude` from the resolved scoped config; treat paths outside scope as not-applicable."

**Estimated scope:** 2-3 hours. Schema change + per-task one-liners.

### Bucket 3 — Two new tasks, **generic from day one**

Both surface from the PHP runs but **neither is PHP-specific**. They use ecosystem-detection (the manifest file present in the repo) to pick the right tool to call.

| Task | What it does | Stack-detected behaviour |
|---|---|---|
| `dep-audit` (new) | Runs the ecosystem's dependency audit and opens a PR pinning to safe versions when known-vulnerable transitive deps exist. | Detect manifest. Run `composer audit` / `npm audit` / `pip-audit` / `cargo audit` / `bundle audit` accordingly. One PR per ecosystem if a monorepo has multiple. |
| `lint-baseline-shrink` (new) | For repos with a static-analysis baseline (`phpstan-baseline.neon`, `psalm-baseline.xml`, `.eslintbaseline.json`, `mypy.ini` ignore list, etc.), pick one entry and fix the underlying issue rather than carrying the suppression. | Detect baseline file. Pick smallest-fix entry. Mirror `add-tests` spirit — chip at debt nightly. |

**These should be deferred until appetite is clear.** Bucket 1 + Bucket 2 are sufficient to call "PHP support" done. dep-audit and lint-baseline-shrink are tasks the framework lacks regardless of stack — adding them when there's demand, with PHP as one of the stacks they cover, is the right shape.

**Estimated scope:** ~3 hours each, when needed.

### Anti-recommendation — what NOT to do

- **Do not add per-stack bundles** (no `bundles/php.md`, no `bundles/drupal.md`). The user's direction here is correct: per-stack bundles duplicate 80% of the generic ones and create a maintenance multiplier we never want. The Shopify bundle is the only exception in the repo, and that's because the Shopify tasks operate on a specific vendored product line (Horizon/Dawn/Skeleton cherry-picks, app-induced migration risk) — not stack-agnostic concerns dressed up.
- **Do not split `translate-ui` into `translate-ui-js` + `translate-ui-php`**. The detection list grows; the task stays one.
- **Do not add a `language:` or `shape:` field to Night Shift Config** unless inference proves insufficient. The `Audit scope` + `Exclude` fields in Bucket 2 give the operator the only knob that actually mattered in the live runs.

## Toolchain question — answered

The "PHP not available in routine sandbox" worry is resolved by run A and run B: `add-tests` ran phpunit suites end-to-end. The sandbox image includes PHP and composer. Therefore:

- **Routine backend works for PHP today.** No change needed in `bundles/_multi-runner.md` to install PHP.
- **GitHub Actions backend remains a valid alternative** for teams that want explicit PHP-version pinning (`shivammathur/setup-php@v2`). For that path, add a conditional setup step to `.github/workflows/night-shift.yml`:

  ```yaml
  - name: Setup PHP (if needed)
    if: ${{ hashFiles('composer.json') != '' }}
    uses: shivammathur/setup-php@v2
    with:
      php-version: ${{ env.PHP_VERSION || '8.3' }}
      extensions: mbstring, xml, curl, sqlite3, intl
      tools: composer:v2
  ```

  This makes the Actions backend polyglot without forcing repos to inline their own setup. Same pattern extends to `setup-python` / `setup-ruby` / `setup-go` later. Optional — only worth doing if/when a PHP team chooses Actions over Routine.

- **`SKILL.md` picker behaviour:** when a target repo has a `composer.json` and no `package.json`, the picker should *not* default-recommend Actions over Routine (earlier draft of this plan said it should — the live runs proved that wrong). Both backends work for PHP. Let the user pick on the same criteria they'd use for a JS repo (Claude Max subscription vs. ANTHROPIC_API_KEY, who pays, etc.).

## Critical files (consolidated)

| File | Bucket | Change |
|---|---|---|
| `bundles/_multi-runner.md` | 1 | Default test/build command lists include PHP commands. |
| `bundles/_multi-runner.md` | 2 | Schema description for `Audit scope` + `Exclude` config fields. |
| `tasks/translate-ui.md` | 1 | Polyglot i18n detection + cross-template string-grep. |
| `tasks/find-security-issues.md` | 1 | Polyglot XSS marker examples. |
| `tasks/improve-seo.md` | 1 | Polyglot auth markers. |
| `tasks/improve-performance.md` | 1 | Restructure audit areas into stack-agnostic buckets. |
| `tasks/improve-accessibility.md` | 1 | Drop JS-only test-lib examples; mention Twig/Blade/JSX. |
| Every code-reading task | 2 | One-line "honor `Audit scope` and `Exclude`". |
| `HOW-TO.md` | 2 | Document the new config fields. |
| `manifest.yml` | 2 | (No change — the new fields live in Night Shift Config, not the manifest.) |
| `skills/night-shift/SKILL.md` | 1 | Bump `NIGHT_SHIFT_VERSION`. |
| (deferred) `tasks/dep-audit.md` | 3 | Generic stack-detected dependency audit. |
| (deferred) `tasks/lint-baseline-shrink.md` | 3 | Generic baseline-shrink task. |

## Verification

1. **Reproduce monolog run** after Bucket 1 lands. The 5 PRs from run A should still appear; no regression in JS routines.
2. **Reproduce symfony-demo run** after Bucket 1 lands. translate-ui should either open a real i18n PR (if it finds gaps in the Symfony translator setup) or self-skip *with a stated reason* — "no hardcoded strings outside `\| trans`" — rather than silently exit because it didn't recognise the framework.
3. **Drupal run after Bucket 2 lands.** Verify tasks honor `Audit scope: web/modules/custom, web/themes/custom` and stay out of `web/modules/contrib`, `web/core`, `vendor`.
4. **Negative test on existing JS routines.** Re-run `night-shift-build` against frisk. No behaviour change should appear; the polyglot lists never *remove* JS coverage, only add.

## Open questions

1. **Was translate-ui's silence on symfony-demo a false negative?** Run B left this ambiguous. The Drupal run (which uses `t()` / `\|t` everywhere in custom modules and themes) is the tiebreaker — if it's also silent, the JS-only detection list is the culprit and Bucket 1 fixes it.
2. **How much does Drupal's contrib-vs-custom split actually trip up audits?** The Drupal run will tell. If tasks correctly stay in custom by default (model inference), Bucket 2 is polish; if they propose contrib PRs, Bucket 2 is required.
3. **Is `add-tests` smart about *not* writing kernel/functional tests on Drupal** where they'd need a real DB the sandbox doesn't have? CLAUDE.md restricts the test command to `--testsuite=unit`, but the task picks *what to test* — if it writes a functional test that needs `SIMPLETEST_BASE_URL`, the verify step will fail.

## Scope estimate

- Bucket 1 (polyglot prompts): ~3 hours, single PR. Largest single edit is `translate-ui.md`. Independently shippable; no migration.
- Bucket 2 (audit-scope config): ~3 hours, single PR. Depends on Bucket 1 only in the sense of file overlap.
- Bucket 3 (new generic tasks): ~3 hours each, optional. Defer until clear demand.

Total to declare "PHP first-class": ~half a day of focused work, two PRs. The framework is closer to ready than the static analysis suggested.
