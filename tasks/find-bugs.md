# Bug Hunt

Look for subtle bugs, missing logic, race conditions, and edge cases. **One PR per issue.**

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: test command, build command, default branch, push protocol. If this task is not in the task list, exit.

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`), operate inside that app only:
- Only scan files under `<app_path>` for bugs.
- Use the app-scoped test and build commands from the scoped config.
- Branch name includes the app slug: `nightshift/bug-<app-slug>-YYYY-MM-DD-<slug>`.
- PR title names the app: `nightshift/bug: <app_path> — <short description>`.

Without an `app_path`, behave as before (whole repo, no app slug in branch / PR title).

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
7. Push and open a PR (prefix the title with `<app_path> — ` when scoped):
   ```
   gh pr create --title "nightshift/bug: <app_path> — <short description>" \
     --body "$(cat <<'EOF'
   ## Bug
   <what is wrong, with file:line>

   ## Repro
   <how the failing test demonstrates it>

   ## Fix
   <what changed>
   EOF
   )"
   ```

## Idempotency
- One bug per night, one PR per issue.
- If a similar PR is already open, skip.
- If no real bugs are found, exit silently. Do not invent bugs.
