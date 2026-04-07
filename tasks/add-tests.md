# Task 05 — Tests

Find coverage gaps and add tests following the project's existing patterns.

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: test command, build command, push protocol. If task 5 is not in the task list, exit.

## Steps
1. Run the project's test command once to confirm a green baseline. If it fails, **exit immediately** — do not try to fix unrelated breakage tonight.
2. Inspect the existing test layout. Mimic the project's chosen framework, file location convention, and assertion style exactly.
3. Identify **one** untested or under-tested unit (module / route / component / utility) where the test would be high-value and low-risk to write. Prefer pure logic over UI / network code.
4. Write the test(s). Follow project conventions for mocks, fixtures, and naming.
5. Run the **full test suite** and the **build command**. Both must pass.
6. If anything fails, do not commit. Revert local changes.

## Commit
```
git add <test-files>
git commit -m "nightshift(tests): add coverage for <unit>"
```
Push using the project's push protocol.

## Idempotency
- One unit per night. Never add tests for many things in one run.
- Do not modify production code in this task. If a test reveals a bug, leave a note in `docs/SUGGESTIONS.md` and stop.
