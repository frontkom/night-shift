# Bug Hunt

Look for subtle bugs, missing logic, race conditions, and edge cases. **One PR per issue.**

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: test command, build command, default branch, push protocol. If the dispatcher passed `allowed_tasks` and `find-bugs` is not in it, exit silently.

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`), operate inside that app only:
- Only scan files under `<app_path>` for bugs.
- Use the app-scoped test and build commands from the scoped config.
- Branch name includes the app slug: `nightshift/bug-<app-slug>-YYYY-MM-DD-<slug>`.
- PR title names the app: `nightshift/bug: <app_path> — <short description>`.

Without an `app_path`, behave as before (whole repo, no app slug in branch / PR title).

## High bar — default is silent
Only open a PR for a bug that is clearly real, clearly the codebase's fault (not a speculative edge case), and whose fix would clearly help the project. Marginal or stylistic concerns, theoretical edge cases that can't actually occur, and hypothetical races you can't reproduce from the code do **not** qualify. **Zero bugs is the correct outcome on most nights** — do not invent or inflate issues to stay busy.

## Steps
1. Check for existing open night-shift bug PRs to avoid duplicates (scope the search to this app when scoped):
   ```
   gh pr list --search "nightshift/bug in:title" --state open
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
   git checkout -b nightshift/bug-<app-slug>-YYYY-MM-DD-<slug>
   # unscoped:
   git checkout -b nightshift/bug-YYYY-MM-DD-<slug>
   ```
5. Add a failing test that demonstrates the bug. Then fix the bug. Test must now pass.
6. Run the scoped **test suite** and the scoped **build command**. Both must pass.
7. Push and open a PR (prefix the title with `<app_path> — ` when scoped). Ensure the standard labels exist first (idempotent), then attach them to the PR. End the body with the Night Shift footer:
   ```
   gh label create nightshift --color "0e8a16" --description "Automated by Night Shift" 2>/dev/null || true
   gh label create "nightshift:audits" --color "1d76db" --description "Night Shift audits bundle" 2>/dev/null || true
   gh pr create --title "nightshift/bug: <app_path> — <short description>" \
     --label nightshift --label "nightshift:audits" \
     --body "$(cat <<'EOF'
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
   )"
   ```

   **Do not** modify `docs/NIGHTSHIFT-HISTORY.md` from this branch — the multi-runner wrapper appends the history row on `main` after you return your one-line result.

## Idempotency
- One bug per night, one PR per issue.
- If a similar PR is already open, skip.
- If no real bugs are found, exit silently. Do not invent bugs.
