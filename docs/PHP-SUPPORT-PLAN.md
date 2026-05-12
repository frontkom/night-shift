# PHP support — PLAN

> **Status: complete (2026-05-12).** All three buckets landed:
> - **Bucket 1** (polyglot prompt edits) — frontkom/night-shift#10.
> - **Bucket 2** (`Audit scope` / `Exclude` config fields) — frontkom/night-shift#10.
> - **Bucket 3** (`dep-audit`, `lint-baseline-shrink`) — frontkom/night-shift#10.
> - **Follow-up review fixes** (slug field in `manifest.yml`, list-dedup, tighter detection tables, yarn-version detection, fallback-divergence note, shopify-task PR-title alignment) — frontkom/night-shift#11.
>
> Verification step (reproduce monolog / symfony-demo / Drupal runs) is being executed against live PHP repos as part of the follow-up PR. Once the verification report lands in `docs/SUGGESTIONS.md` (or as a comment on the follow-up PR), this plan can be archived or deleted.

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

### Run C — `perandre/fagskolen-viken` (Drupal CMS, private) — session `01LW6Sdz71agJQvngYBSdaMg`

8 PRs in ~22 minutes against the develop branch of a real production Drupal codebase mirrored from `frontkom/fagskolen-viken`. Notable:

| PR | Task | Result |
|---|---|---|
| #1 +22/-5 | update-user-guide | README refresh |
| #2 +30/-0 | document-decisions | ADR for the Gutenberg editor choice — drew on `content_gutenberg/`, composer dep `drupal/gutenberg`, and CKEditor history |
| #3 +31/-0 | suggest-improvements | Three ideas |
| #4 +365/-0 | add-tests | 2 unit tests under `web/modules/custom/fagskolene_studies/tests/src/Unit/` — **canonical Drupal layout used correctly** (`tests/src/Unit/EventSubscriber/`, `tests/src/Unit/Schema/`). `composer install` failed locally ("CKEditor 4 retirement blocks dependency resolution") so tests weren't run; PR body said so explicitly and noted both classes target pure-PHP logic that doesn't need Drupal bootstrap. |
| #5 +5/-5 | improve-accessibility | WCAG 2.1 AA sweep against custom Twig themes |
| #6 +1/-1 | find-bugs | **Real production bug:** `SITE_SLUG = 'oslo'` in `viken.theme:20` — copy-paste artifact from when the Viken theme was forked from the Oslo site. Caused the `<html>` element to get class `.oslo` instead of `.viken`, activating the wrong (blue Oslo, not orange Viken) CSS in the footer. Surgical +1/-1 fix in custom theme code with grep-verification that no other `.oslo` references needed updating. |
| #7 +11/-0 | improve-seo | **Drupal-aware SEO fix:** modified `config/sync/metatag.metatag_defaults.{global,front,node,node__article}.yml` — the canonical Drupal metatag location — using token defaults (`[node:title]`, `[site:name]`) rather than hardcoded strings. PR body included a self-aware "Drupal-shape observation" calling out what the framework should learn. |
| #8 +85/-78 | improve-performance | **Expert-level Drupal perf fix:** N+1 in `viken_get_course_details()` refactored from 45 queries to 3 using `loadMultiple()` and entity field API instead of raw `\Drupal::database()->select()`. Documented an unchanged 400-line preprocess function with reasons (entity static cache partially mitigates; control flow makes refactor riskier). |

Silent: `translate-ui`, `find-security-issues`, `update-changelog`, `build-planned-features`, `work-on-issues`, `triage-ci-failures`. (Some correct, some ambiguous — see Drupal findings below.)

#### Findings — fagskolen-viken (Drupal)

**Toolchain.** The probe wasn't paste-back-able from the routine session (PR-only audit trail), but the implicit signal is clear: PHP and composer are present; `composer install` failed on this real-world repo due to CKEditor 4 retirement breaking dependency resolution. **add-tests handled this gracefully** — wrote unit-only tests, said "couldn't run locally" in the PR body, picked tests targeting pure-PHP logic. This is the right shape; no framework change needed for the failure mode itself, but documenting the pattern in the `add-tests` task ("if `composer install` fails, still write the tests, mark verification as deferred in PR body") would harden the convention.

**Custom-vs-contrib scoping was correct by inference.** Every task that wrote code touched `web/themes/custom/` or `web/modules/custom/`. Nothing was proposed against `web/modules/contrib/`, `web/core/`, or `vendor/`. This is a major positive: the model inferred the customary scope from the repo's directory naming without needing an explicit `Audit scope` config field. **Bucket 2 (audit-scope config) drops from "required" to "useful polish"** — repos that name their dirs sensibly don't need it.

**Drupal-shape awareness.** The model recognised:
- `web/modules/custom/<module>/tests/src/Unit/` as the canonical Drupal unit-test location (PSR-4 namespace `Drupal\Tests\<module>\Unit\...`).
- `config/sync/metatag.metatag_defaults.*.yml` as Drupal's metatag module config — modified there rather than in Twig templates, which is correct for site-wide defaults.
- `loadMultiple()` + entity field API as Drupal's batching primitive over `->load()` in a loop + raw `\Drupal::database()->select()`.
- `hook_preprocess_*` functions in `*.theme` files as the rendering pipeline to audit for perf.
- The custom-vs-contrib boundary (`web/modules/custom/` is "ours", `web/modules/contrib/` is vendored).

None of this is encoded in the existing task prompts — the model derived it from the repo's structure. That makes the "shape detection via inference" approach robust enough that we don't need a `shape: drupal` config flag.

**The one Drupal-shape gap is template-language audit.** improve-accessibility only modified +5/-5 across the sweep — small. The Drupal theme has many Twig templates; the modest output may indicate the task didn't deeply audit all of them, or that the templates were already broadly accessible. Inconclusive from outside the session.

**Translate-ui was silent on Drupal.** Strong evidence for the JS-bias hypothesis: this codebase has a Norwegian site language and uses Drupal's `t()` / `|t` everywhere in custom modules and themes. If the framework recognised the Drupal i18n pattern, the most likely outcome is a `silent | no hardcoded user-visible strings outside t()` decision; if it didn't, the silence is because the detection list `(next-intl, react-i18next, formatjs, custom)` doesn't match Drupal. Either way, **Bucket 1's translate-ui edit (polyglot detection) is necessary** — even if today's silence is correct, the prompt is over-specific and will fail on other PHP setups.

**PR-convention violations on improve-seo and improve-performance.** Both PRs landed with non-conforming branch names (`night-shift/improve-seo` and `night-shift/improve-performance` instead of `night-shift/seo-YYYY-MM-DD` / `night-shift/perf-YYYY-MM-DD`) and PR titles without the `night-shift/<area>:` prefix. The label sweep correctly added the `night-shift` label, so the audit trail is intact, but this is a **framework consistency bug independent of PHP support**. Likely cause: the bundle dispatcher passed `improve-seo` / `improve-performance` as the task name and the subagent used that verbatim instead of consulting `bundles/_multi-runner.md → "Branch and PR naming"`. Worth a separate fix in `_multi-runner.md` or the audits bundle prompt to assert the convention more loudly inside subagent prompts.

**PRs opened:** `gh pr list --label night-shift -R perandre/fagskolen-viken --state all`

## Key takeaways across all three runs

1. **PHP and composer are in the routine sandbox.** `add-tests` ran the full PHPUnit suites for monolog (1173 tests, 2142 assertions) and symfony-demo (53 tests) with zero toolchain setup. On Drupal, `composer install` failed due to a real-world brittleness (CKEditor 4 retirement), but the task wrote unit-only tests targeting pure-PHP logic and was honest about the unverified state in the PR body. The "what if PHP isn't available" worry can be dropped — routine backend is viable for PHP today.

2. **The audit tasks generalise without modification.** find-bugs caught a constructor-order bug in monolog AND a copy-paste config leftover (`SITE_SLUG = 'oslo'` in the Viken theme) — two qualitatively different real bugs in idiomatic PHP. improve-performance caught a Doctrine N+1 in Symfony AND a 45-query → 3-query Drupal `loadMultiple()` refactor. improve-seo correctly classified Symfony admin routes AND modified Drupal's `config/sync/metatag.*.yml` files (not Twig templates) for site-wide defaults. **The model derives shape-specific behaviour from the repo's directory structure and naming conventions — no `shape:` config field is needed.**

3. **Translate-ui is the one over-specific prompt that matters.** Silent on monolog (correct — library), silent on symfony-demo (ambiguous), silent on Drupal (**likely incorrect** — the Drupal codebase uses `t()` / `\|t` everywhere in custom modules and themes). Bucket 1's translate-ui edit (polyglot detection list) is the load-bearing prompt fix in this plan.

4. **Custom-vs-contrib scoping works by inference.** All Drupal audits stayed in `web/themes/custom/` and `web/modules/custom/`; none proposed changes against `web/modules/contrib/`, `web/core/`, or `vendor/`. **Bucket 2 (audit-scope config field) drops from "required" to "useful polish"** for repos that name their dirs sensibly. Keep the change in the plan but mark it lower priority.

5. **PR-naming convention drifts on some Drupal subagent dispatches.** Both improve-seo and improve-performance produced PRs with branch `night-shift/improve-seo` (no date) and PR titles missing the `night-shift/<area>:` prefix. The label sweep saved the audit trail, but the convention compliance is a framework consistency bug independent of PHP — the bundle/audit dispatcher probably passes the task ID (`improve-seo`, `improve-performance`) as the branch slug verbatim in some path. Worth fixing in `bundles/_multi-runner.md` or the audits bundle subagent prompt.

6. **Routine model wins for PHP today.** Doc + audit tasks need no toolchain beyond what's in the sandbox. `add-tests` runs PHPUnit cleanly on small/medium repos and gracefully degrades on real-world repos where `composer install` is fragile. GitHub Actions backend remains a reasonable alternative for teams that want explicit PHP-version pinning, but it is not required.

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
| `bundles/audits.md` (or each audit task) | Assert branch + PR-title convention more loudly inside the subagent prompt. The Drupal run produced two PRs (`night-shift/improve-seo`, `night-shift/improve-performance`) where the subagent used the task ID as the branch slug instead of the `<area>` slug (`seo`, `perf`) prescribed by `_multi-runner.md`. This is a framework consistency bug independent of PHP — but it surfaces here, so fold the fix into the same PR. |
| `tasks/add-tests.md` | Add a paragraph: "If `composer install` (or the project's dependency install command) fails — common on real-world repos with abandoned/patched packages — still write the unit tests, prefer ones that don't need the framework's bootstrap, and document the unverified state in the PR body. The fagskolen-viken Drupal run hit this and handled it correctly; codify the pattern." |
| `skills/night-shift/SKILL.md` | Bump `NIGHT_SHIFT_VERSION` per `CLAUDE.md` workflow rule (frontmatter + HTML comment line). |

**Estimated scope:** 2-3 hours of careful prompt editing. Single PR. Lifts signal on JS repos too (the prompts get cleaner regardless of stack).

### Bucket 2 — Generic config: `Audit scope` and `Exclude` (lower priority)

**Drupal run revealed this is polish, not required.** All Drupal audits correctly inferred the custom/contrib boundary from directory names and stayed in `web/themes/custom/` + `web/modules/custom/`. The plan still includes this for cases where inference fails (e.g. a project that names its custom dirs unconventionally, or one where the team wants to constrain audits to a subset of even the custom code), but Bucket 2 is no longer blocking PHP/Drupal support.

Production CMSes (Drupal especially, but also any large PHP/Rails/JS app with vendored code) have a recurring pattern Night Shift's tasks don't *explicitly* model: **most of the code in the repo is vendored** and audit PRs against it get rejected on sight. Drupal puts contrib modules under `web/modules/contrib/`, Drupal core under `web/core/`, libraries under `vendor/`. WordPress puts plugins under `wp-content/plugins/` (some custom, most vendored). JS apps put deps under `node_modules/` and sometimes also `vendor/` for monorepo internal packages.

Today the framework relies on the model to figure this out from context. The Drupal run confirmed that works for canonical layouts. The explicit config field is for the cases it doesn't.

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

## Open questions — answered by the three runs

1. ~~Was translate-ui's silence on symfony-demo a false negative?~~ **Likely yes.** Drupal — which uses `t()` / `|t` pervasively — was also silent. Two silent skips on PHP repos that demonstrably have i18n setups is strong evidence the detection list is the problem. Bucket 1's translate-ui edit confirmed as load-bearing.
2. ~~How much does Drupal's contrib-vs-custom split trip up audits?~~ **It doesn't, by inference.** All Drupal audits stayed in `web/themes/custom/` + `web/modules/custom/`. Bucket 2 demoted from required to polish.
3. ~~Is `add-tests` smart about not writing DB-dependent tests on Drupal?~~ **Yes.** Both tests written (`ProgramSchemaBuilderTest`, `LegacyFilterRedirectSubscriberTest`) target pure-PHP logic with no Drupal bootstrap. The task picked targets where verification didn't need a database, even though it couldn't run the verification (composer install failed). The plan's add-tests addition formalizes this pattern.

## Remaining open questions

1. **Is the PR-naming-convention drift on Drupal audits reproducible?** monolog and symfony-demo audits produced correctly-prefixed branches (`night-shift/perf-2026-05-12`, `night-shift/security-secrets-2026-05-12`). Drupal produced two non-conforming branches (`night-shift/improve-seo`, `night-shift/improve-performance`). Either a model-side fluke, or the `bundles/audits.md` subagent prompt is less clear than the others. Worth checking — and the fix is cheap regardless.
2. **Should the routine sandbox image add common PHP extensions** (mbstring, xml, curl, sqlite3, intl, gd) by default, so DB-using Symfony/Laravel test runs don't fail mid-suite? Out of scope for this plan — that's an Anthropic-side question. For now, projects that need extensions beyond defaults should declare them in their `CLAUDE.md` (a new `PHP extensions:` field, if Bucket 2 lands).

## Scope estimate

- Bucket 1 (polyglot prompts): ~3 hours, single PR. Largest single edit is `translate-ui.md`. Independently shippable; no migration.
- Bucket 2 (audit-scope config): ~3 hours, single PR. Depends on Bucket 1 only in the sense of file overlap.
- Bucket 3 (new generic tasks): ~3 hours each, optional. Defer until clear demand.

Total to declare "PHP first-class": ~half a day of focused work, two PRs. The framework is closer to ready than the static analysis suggested.
