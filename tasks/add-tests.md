# Tests

Find coverage gaps and add tests following the project's existing patterns.

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: test command, build command, push protocol. If this task is not in the task list, exit.

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`), operate inside that app only:
- Only walk files under `<app_path>` when hunting for coverage gaps.
- Use the app-scoped test and build commands from the scoped config.
- Commit message names the app: `nightshift(tests): <app_path> — add coverage for <unit>`.

Without an `app_path` (single-app repo), behave as before: walk the whole repo, use the top-level test/build commands, commit without an app prefix.

## Steps
1. Run the scoped test command once to confirm a green baseline. If it fails, **exit immediately** — do not try to fix unrelated breakage tonight.
2. Inspect the existing test layout **under `<app_path>`** (or repo-wide when unscoped). Mimic the project's chosen framework, file location convention, and assertion style exactly.
3. Identify **one** untested or under-tested unit (module / route / component / utility) **inside `<app_path>`** where the test would be high-value and low-risk to write. Prefer pure logic over UI / network code.
4. Write the test(s). Follow project conventions for mocks, fixtures, and naming. Do not touch files outside `<app_path>` when scoped.
5. Run the scoped **test suite** and the scoped **build command**. Both must pass.
6. If anything fails, do not commit. Revert local changes.

## Commit
```
# scoped:
git add <test-files>
git commit -m "nightshift(tests): <app_path> — add coverage for <unit>"
# unscoped:
git commit -m "nightshift(tests): add coverage for <unit>"
```
Push using the project's push protocol.

## Idempotency
- One unit per night. Never add tests for many things in one run.
- Do not modify production code in this task. If a test reveals a bug, leave a note in `docs/SUGGESTIONS.md` and stop.
