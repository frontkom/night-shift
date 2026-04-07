# Task 09 — Bug Hunt

Look for subtle bugs, missing logic, race conditions, and edge cases. **One PR per issue.**

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: test command, build command, default branch, push protocol. If task 9 is not in the task list, exit.

## Steps
1. Check for existing open night-shift bug PRs to avoid duplicates:
   ```
   gh pr list --search "nightshift/bug in:title" --state open
   ```
2. Look for:
   - Off-by-one errors and boundary conditions
   - Missing null/undefined checks on values that obviously can be missing
   - `async` flows missing `await` or unhandled rejections
   - Race conditions (state updates during in-flight requests, missing cancellation)
   - Wrong-direction comparisons, inverted conditionals
   - Missing error handling on external IO that the rest of the code assumes succeeds
   - Date/timezone bugs (server vs client, DST, ISO parsing)
   - Pagination, sort, filter combinations that produce wrong results
3. Pick **one** real bug tonight. It must be reproducible from reading the code — not a hypothetical.
4. Create a branch:
   ```
   git checkout -b nightshift/bug-YYYY-MM-DD-<slug>
   ```
5. Add a failing test that demonstrates the bug. Then fix the bug. Test must now pass.
6. Run the **full test suite** and the **build command**. Both must pass.
7. Push and open a PR:
   ```
   gh pr create --title "nightshift/bug: <short description>" \
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
