# Lint Baseline Shrink

For repos that carry a static-analysis baseline file (an inventory of suppressed/grandfathered warnings), pick **one** entry, fix the underlying issue, and remove the suppression. **One PR with one fewer baseline entry.**

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: test command, build command, default branch, push protocol. If the dispatcher passed `allowed_tasks` and `lint-baseline-shrink` is not in it, exit silently.

**Audit scope.** Honor `Audit scope`, `Exclude`, and the **hardcoded baseline exclude** defined in `bundles/_multi-runner.md` → "Optional config fields" (single source of truth — do not inline the list here). Only fix violations whose target file lives inside `Audit scope` (when set); never edit code under `Exclude` or the baseline list.

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`), operate inside that app only:
- Look for baseline files **under `<app_path>`** first; fall back to the repo root only if none exist.
- Use the app-scoped test and build commands from the scoped config.
- Branch: `night-shift/lint-baseline-<app-slug>-YYYY-MM-DD`.
- PR title: `night-shift/lint-baseline: <app_path> — shrink <tool> baseline by 1`.

Without an `app_path`, behave repo-wide.

## High bar — default is silent
Open a PR **only** when:
1. A baseline file exists for at least one supported tool (see detection table below), **and**
2. The smallest-fix entry can be resolved with a clearly correct, narrowly-scoped change (one file, one obvious fix), **and**
3. Removing the suppression and re-running the tool yields the same clean result as before (no new findings surface).

If the smallest entry's fix would require a refactor, a behavioral change, or guessing at intent, exit silently — leave that entry for a human.

**Deliberately stricter than `add-tests`.** `add-tests` has an exception that allows writing unit-only tests when dependency install fails. This task has **no** such exception: claiming "one fewer baseline entry" requires the tool itself to re-run cleanly, which requires a working dep install. If `composer install` / `npm install` / `bundle install` / etc. fails, or if the scoped test or build command regresses after the fix, exit silently. Leave the entry for a human.

## Steps

1. Check for an existing open night-shift lint-baseline PR for this app (or repo when unscoped):
   ```
   gh pr list --search "night-shift/lint-baseline in:title" --state open
   ```
   If one exists for the same app, exit silently — do not stack PRs.

2. **Detect the baseline file.** Look for any of these *canonical* baseline files (best-effort detection — if you find something that looks similar but isn't on this list, exit silently rather than guess; a misidentified "baseline" risks editing a cache file or per-module silencing block instead of a true debt inventory). Pick the first one present; if multiple, pick the one with the most entries (largest debt → most appetite to chip away).

   | Baseline file | Tool | Notes | Re-run command |
   |---|---|---|---|
   | `phpstan-baseline.neon` | PHPStan | Must be referenced from `phpstan.neon` / `phpstan.dist.neon`. Auto-regenerated. | `vendor/bin/phpstan analyse --no-progress` |
   | `psalm-baseline.xml` | Psalm | Must be referenced from `psalm.xml`. Auto-regenerated. | `vendor/bin/psalm --no-progress` |
   | `phpcs-baseline.xml` | PHP_CodeSniffer | Only valid if the `phpcs-baseline` (or equivalent) plugin is listed in `composer.json`. Skip `.phpcs-cache` — that's a cache file, not a baseline. | `vendor/bin/phpcs` |
   | `.rubocop_todo.yml` | RuboCop | Hand-maintained or generated via `rubocop --auto-gen-config`. | `bundle exec rubocop` |
   | `mypy_baseline.json` (or whatever the project's `mypy_baseline` config points at) | mypy | Only valid if the `mypy_baseline` package is installed. Skip `mypy.ini` `[mypy-*]` blocks — those are per-module silencing, not a debt inventory. | `mypy .` |
   | `pylint-baseline.json` | Pylint | Only valid if produced by a checked-in snapshot (`pylint --output-format=json > pylint-baseline.json`); skip ad-hoc CI artefacts. | `pylint .` |
   | An ESLint baseline file checked into the repo (filename varies — `.eslint-baseline.json`, `eslint-baseline.json`, etc.) | ESLint | Only valid if the project uses an explicit ESLint baseline plugin referenced from `.eslintrc*` / `eslint.config.*`. Skip if the only inventory is `eslint-disable` comments scattered across the codebase. | `npx eslint .` |

   **TypeScript intentionally omitted.** TS has no canonical baseline-file format; `// @ts-expect-error` comments live inline and are out of scope for this task. If a project uses a custom TS-snapshot approach, document it in `CLAUDE.md` and treat it as a project-specific extension.

   If none of these canonical files are present, exit silently — there is no baseline to shrink.

3. **Pick the smallest-fix entry.** Read the baseline file. For each entry, the "smallest fix" heuristic is:
   - Single file (not a regex / glob across many files).
   - A single rule code (not a bundle of unrelated suppressions).
   - The underlying violation is one of these well-understood shapes: missing type annotation, unused import/variable, missing strict null check, dead code, simple naming-convention nit, or a missing `final`/`readonly` modifier.

   Skip entries that involve: cross-file refactors, behavioral changes, complex generic-type wrangling, "TODO investigate" comments, or anything that looks like it was suppressed *because* a fix is non-trivial.

   If no entry meets the heuristic, exit silently.

4. **Fix the underlying issue.** Make the smallest change that resolves the violation as the tool reports it. Do not "while-you're-there" cleanups; do not touch unrelated lines.

5. **Remove the suppression** from the baseline file. If the baseline is auto-generated (PHPStan, Psalm), the recommended pattern is:
   - Edit the source to fix the issue.
   - Re-run the tool's baseline regenerator (`vendor/bin/phpstan analyse --generate-baseline`, `vendor/bin/psalm --set-baseline=psalm-baseline.xml`).
   - Confirm the diff to the baseline file is exactly the one entry's removal — nothing else.
   - If unrelated entries also disappear or appear, revert and exit silently (the baseline is stale / not-faithful and needs a human regeneration pass first).

   For hand-maintained baselines (`.rubocop_todo.yml`, `mypy.ini`), edit the file directly and remove only the line(s) for the picked entry.

6. **Re-run the tool** and confirm: zero new findings, one fewer baseline entry, exit code 0.

7. **Verify nothing else broke.** Run the scoped **test suite** and the scoped **build command**. Both must pass.

8. Create the branch:
   ```
   # scoped:
   git checkout -b night-shift/lint-baseline-<app-slug>-YYYY-MM-DD
   # unscoped:
   git checkout -b night-shift/lint-baseline-YYYY-MM-DD
   ```

9. Push and open the PR (prefix title with `<app_path> — ` when scoped). The wrapper has already created the standard labels for this repo — just attach them. **Always use `--body-file`, never inline `--body`.** End the body with the Night Shift footer:
   ```
   cat > /tmp/night-shift-pr-body.md <<'EOF'
   ## Plain summary
   <1-2 sentences in English (PR review is always in English, regardless of the product's user language). What kind of warning used to be suppressed, what the fix changed, and why this is one fewer thing for humans to wade through. No rule-code jargon. See bundles/_multi-runner.md → "Body header — Plain summary".>

   ## Summary
   Shrunk the `<tool>` baseline by one entry by fixing the underlying violation.

   ## Entry removed
   - `<file>:<line>` — `<rule>` — <one-line description of the violation and the fix>

   ## Verification
   - `<tool re-run cmd>`: clean, one fewer baseline entry.
   - Test suite and build: passing.

   ---
   _Run by Night Shift • code-fixes/lint-baseline-shrink_
   EOF

   # Stagger PR creation. Spec: bundles/_multi-runner.md → "PR creation throttle".
   LAST=/tmp/night-shift-pr-last-created
   if [ -f "$LAST" ]; then
     ELAPSED=$(( $(date +%s) - $(cat "$LAST") ))
     [ "$ELAPSED" -lt 90 ] && sleep "$((90 - ELAPSED))"
   fi
   PR_URL=$(gh pr create --title "night-shift/lint-baseline: <app_path> — shrink <tool> baseline by 1" \
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
- One baseline entry per PR. Never bundle multiple fixes — the value is the chip-away cadence, not throughput.
- If a sibling night-shift/lint-baseline PR is already open, exit silently.
- If no baseline file is present, or every remaining entry fails the smallest-fix heuristic, exit silently. **Never** suppress a different entry just to keep the count even.
