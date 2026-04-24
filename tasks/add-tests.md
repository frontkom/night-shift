# Tests

Find coverage gaps and add both **unit tests** and **e2e tests** following the project's existing patterns. **One PR with up to 10 new tests total.**

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: test command, build command, default branch, push protocol. If the dispatcher passed `allowed_tasks` and `add-tests` is not in it, exit silently.

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`), operate inside that app only:
- Only walk files under `<app_path>` when hunting for coverage gaps.
- Use the app-scoped test and build commands from the scoped config.
- Branch: `night-shift/tests-<app-slug>-YYYY-MM-DD`.
- PR title: `night-shift/tests: <app_path> — add coverage for <N> units`.

Without an `app_path` (single-app repo), behave as before: walk the whole repo, use the top-level test/build commands.

## Steps
1. Check for an existing open night-shift tests PR for this app (or repo when unscoped):
   ```
   gh pr list --search "night-shift/tests in:title" --state open
   ```
   If one exists for the same app, exit silently — do not stack PRs.

2. **Understand the project's testing approach before writing anything.** Before creating any tests:
   - Look for test plans or testing guides in `docs/`, `TESTING.md`, `CLAUDE.md`, or similar markdown files that describe how tests should be structured.
   - Scan existing test files to understand frameworks, file locations, naming conventions, helper utilities, fixtures, and assertion style.
   - For **unit tests**: identify the framework (Jest, Vitest, pytest, Go testing, etc.) and mimic the existing patterns exactly.
   - For **e2e tests**: check if Playwright, Cypress, or another e2e framework is already set up. If no e2e framework exists, use **Playwright** as the default. Check for existing page objects, test helpers, or base fixtures to build on.

3. Run the scoped test command once to confirm a green baseline. If it fails, **exit immediately** — do not try to fix unrelated breakage tonight.

4. Identify **up to 10** coverage gaps across the application — aim for a mix of both types:
   - **Unit tests** for untested utilities, business logic, data transformations, hooks, components, API handlers, or model methods.
   - **E2e tests** for untested user flows, critical paths, form submissions, navigation, or interactive features.
   
   Prioritize areas with no existing test coverage. Stop at 10 even if more gaps exist.

5. Write tests for each identified gap. Follow the conventions discovered in step 2. Do not touch files outside `<app_path>` when scoped.

6. Run the scoped **test suite** and the scoped **build command** after each test file. If a test is flaky or fails, revert that test file and continue with the next unit. Do not commit failing tests.

7. Collect all passing tests in one branch (include app slug when scoped):
   ```
   # scoped:
   git checkout -b night-shift/tests-<app-slug>-YYYY-MM-DD
   # unscoped:
   git checkout -b night-shift/tests-YYYY-MM-DD
   ```
8. Push and open the PR (prefix title with `<app_path> — ` when scoped). The wrapper has already created the standard labels for this repo — just attach them. **Always use `--body-file`, never inline `--body`.** End the body with the Night Shift footer:
   ```
   cat > /tmp/night-shift-pr-body.md <<'EOF'
   ## Summary
   Found coverage gaps and added tests for <N> units.

   ## Unit tests added
   - <bullet per test file, naming the unit under test>

   ## E2e tests added
   - <bullet per test file, describing the user flow covered>

   ## Verification
   - All tests pass locally

   ---
   _Run by Night Shift • code-fixes/add-tests_
   EOF

   PR_URL=$(gh pr create --title "night-shift/tests: <app_path> — add coverage for <N> units" \
     --label night-shift --label "night-shift:code-fixes" \
     --body-file /tmp/night-shift-pr-body.md)
   # Post-create ritual (spec: bundles/_multi-runner.md)
   gh pr edit "$PR_URL" --add-label night-shift --add-label "night-shift:code-fixes"
   BODY=$(gh pr view "$PR_URL" --json body -q .body)
   case "$BODY" in *'\n'*) printf '%s' "$BODY" | python3 -c "import sys;sys.stdout.write(sys.stdin.read().replace(chr(92)+chr(110),chr(10)))" > /tmp/night-shift-body-fix.md && gh pr edit "$PR_URL" --body-file /tmp/night-shift-body-fix.md ;; esac
   gh pr merge "$PR_URL" --auto --squash 2>/dev/null || gh pr merge "$PR_URL" --auto || true
   ```

   **Self-review.** After the post-create ritual above, run the **Self-review + one revision** step from `_multi-runner.md` before returning your one-line result. One review, at most one revision commit, same branch; if the revision breaks tests, revert with `git push --force-with-lease` and keep the original PR.

   **Do not** modify `docs/NIGHTSHIFT-HISTORY.md` from this branch — the multi-runner wrapper appends the history row on `main` after you return your one-line result.

## Idempotency
- One sweep PR open at a time.
- Do not modify production code in this task. If a test reveals a bug, leave a note in `docs/SUGGESTIONS.md` and stop.
- If no meaningful coverage gaps remain, exit silently.
