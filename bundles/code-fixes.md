# Code fixes bundle

You are running the Night Shift **Code fixes** bundle on this repository.

**Before doing anything else**, print a single status line so the user sees immediate output:
`Night Shift code-fixes bundle starting on <repo-name>...`

## Setup
Read `CLAUDE.md` for the **Night Shift Config** section if present. If absent, use defaults — see `_multi-runner.md`.

## Resolve tasks from manifest

Fetch and parse https://raw.githubusercontent.com/frontkom/night-shift/main/manifest.yml.

- Read `bundles.code-fixes` for this bundle's settings.
- Read `tasks[]` and select all entries where `bundle: code-fixes`. Sort by `order` ascending. This is the canonical task list — **do not** rely on a hardcoded list anywhere else.
- **Allowlist filter.** If the dispatcher passed `allowed_tasks` (a list of task ids), intersect the bundle's task list against it. Tasks not in `allowed_tasks` are skipped entirely. Absent `allowed_tasks` = all tasks allowed.

## Execute

For each task in order:

1. Fetch `https://raw.githubusercontent.com/frontkom/night-shift/main/tasks/<task-id>.md`.
2. Execute the task exactly as written.
3. After each task commits, re-run the project's test and build commands to confirm a healthy baseline before the next task begins.
4. Apply the bundle's rules from the manifest. Code-fixes is `parallelism: sequential`, `stop_on_failure: true` — if any task's verification (test or build) fails, **STOP the bundle immediately**.
5. If a task says "exit silently", that is success — continue with the next.

## Mode

Per the manifest, this bundle is **pull-request** mode. Each task creates a feature branch and opens a PR for review.
