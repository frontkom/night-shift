# Bug Hunt

Look for subtle bugs, missing logic, race conditions, and edge cases. **One PR per issue.**

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: test command, build command, default branch, push protocol. If the dispatcher passed `allowed_tasks` and `find-bugs` is not in it, exit silently.

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`), operate inside that app only:
- Only scan files under `<app_path>` for bugs.
- Use the app-scoped test and build commands from the scoped config.
- Branch name includes the app slug: `night-shift/bug-<app-slug>-YYYY-MM-DD-<slug>`.
- PR title names the app: `night-shift/bug: <app_path> — <short description>`.

Without an `app_path`, behave as before (whole repo, no app slug in branch / PR title).

## High bar — default is silent
Only open a PR for a bug that is clearly real, clearly the codebase's fault (not a speculative edge case), and whose fix would clearly help the project. Marginal or stylistic concerns, theoretical edge cases that can't actually occur, and hypothetical races you can't reproduce from the code do **not** qualify. **Zero bugs is the correct outcome on most nights** — do not invent or inflate issues to stay busy.

## Steps
1. Check for existing open night-shift bug PRs to avoid duplicates (scope the search to this app when scoped):
   ```
   gh pr list --search "night-shift/bug in:title" --state open
   ```
2. Look for (inside `<app_path>` when scoped):
   - Off-by-one errors and boundary conditions
   - Missing null/undefined checks on values that obviously can be missing
   - `async` flows missing `await` or unhandled rejections
   - Race conditions (state updates during in-flight requests, missing cancellation)
   - Wrong-direction comparisons, inverted conditionals
   - Missing error handling on external IO that the rest of the code assumes succeeds
   - Date/timezone bugs (server vs client, DST, ISO parsing)
   - Pagination, sort, filter combinations that produce wrong results
3. Pick **one** real bug tonight. It must be reproducible from reading the code — not a hypothetical. When scoped, the bug and its fix must live under `<app_path>`.
4. Create a branch (include the app slug when scoped):
   ```
   # scoped:
   git checkout -b night-shift/bug-<app-slug>-YYYY-MM-DD-<slug>
   # unscoped:
   git checkout -b night-shift/bug-YYYY-MM-DD-<slug>
   ```
5. Add a failing test that demonstrates the bug. Then fix the bug. Test must now pass.
6. Run the scoped **test suite** and the scoped **build command**. Both must pass.
7. Push and open a PR (prefix the title with `<app_path> — ` when scoped). The wrapper has already created the standard labels for this repo — just attach them. **Always use `--body-file`, never inline `--body`.** End the body with the Night Shift footer:
   ```
   cat > /tmp/night-shift-pr-body.md <<'EOF'
   ## Plain summary
   <1-2 sentences in English (PR review is always in English, regardless of the product's user language). Who was affected, what did they experience, what changes now. No symbol names, no file paths, no error classes. See bundles/_multi-runner.md → "Body header — Plain summary" for the full convention.>

   ## Bug
   <what is wrong, with file:line>

   ## Repro
   <how the failing test demonstrates it>

   ## Fix
   <what changed>

   ---
   _Run by Night Shift • audits/find-bugs_
   EOF

   PR_URL=$(gh pr create --title "night-shift/bug: <app_path> — <short description>" \
     --label night-shift \
     --body-file /tmp/night-shift-pr-body.md)
   # Post-create ritual — REQUIRED after every gh pr create. Do NOT return to the wrapper without running every line below. Skipping leaves PR bodies flattened (literal \n on GitHub) or auto-merge unarmed. Spec: bundles/_multi-runner.md.
   gh pr edit "$PR_URL" --add-label night-shift
   BODY=$(gh pr view "$PR_URL" --json body -q .body)
   case "$BODY" in *'\n'*) printf '%s' "$BODY" | python3 -c "import sys;sys.stdout.write(sys.stdin.read().replace(chr(92)+chr(110),chr(10)))" > /tmp/night-shift-body-fix.md && gh pr edit "$PR_URL" --body-file /tmp/night-shift-body-fix.md ;; esac
   gh pr merge "$PR_URL" --auto --squash 2>/dev/null || gh pr merge "$PR_URL" --auto || true
   ```

   **Self-review.** After the post-create ritual above, run the **Self-review + one revision** step from `_multi-runner.md` before returning your one-line result. One review, at most one revision commit, same branch; if the revision breaks tests, revert with `git push --force-with-lease` and keep the original PR.

## Idempotency
- One bug per night, one PR per issue.
- If a similar PR is already open, skip.
- If no real bugs are found, exit silently. Do not invent bugs.
