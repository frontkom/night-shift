# Plans bundle

You are running the Night Shift **Plans** bundle on this repository.

**Before doing anything else**, print a single status line so the user sees immediate output:
`Night Shift plans bundle starting on <repo-name>...`

## Setup
Read `CLAUDE.md` for the **Night Shift Config** section if present. If absent, use defaults — see `_multi-runner.md`.

## Resolve tasks from manifest

Fetch and parse https://raw.githubusercontent.com/frontkom/night-shift/main/manifest.yml.

- Read `bundles.plans` for this bundle's settings (`parallelism`, `stop_on_failure`, `mode`).
- Read `tasks[]` and select all entries where `bundle: plans`. Sort by `order` ascending. This is the canonical task list — **do not** rely on a hardcoded list anywhere else.
- **Allowlist filter.** If the dispatcher passed `allowed_tasks` (a list of task ids), intersect the bundle's task list against it. Tasks not in `allowed_tasks` are skipped entirely (no fetch, no execute). Absent `allowed_tasks` = all tasks allowed.

## Execute

For each task in order:

1. Fetch `https://raw.githubusercontent.com/frontkom/night-shift/main/tasks/<task-id>.md` (where `<task-id>` is the task's `id` field from the manifest).
2. Execute the task exactly as written, including its commit and PR steps.
3. Apply the bundle's rules from the manifest:
   - `parallelism: independent` and `stop_on_failure: false` — one task's exit must not affect the others.
4. If a task says "exit silently", that is success — continue with the next.

## Mode

Per the manifest, this bundle is **pull-request** mode. Tasks create feature branches and open PRs, never commit directly to the default branch.
