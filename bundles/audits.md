# Audits bundle

You are running the Night Shift **Audits** bundle on this repository.

**Before doing anything else**, print a single status line so the user sees immediate output:
`Night Shift audits bundle starting on <repo-name>...`

## Setup
Read `CLAUDE.md` for the **Night Shift Config** section if present. If absent, use defaults — see `_multi-runner.md`.

## Resolve tasks from manifest

Fetch and parse https://raw.githubusercontent.com/frontkom/night-shift/main/manifest.yml.

- Read `bundles.audits` for this bundle's settings.
- Read `tasks[]` and select all entries where `bundle: audits`. Sort by `order` ascending. This is the canonical task list — **do not** rely on a hardcoded list anywhere else.
- **Allowlist filter.** If the dispatcher passed `allowed_tasks` (a list of task ids), intersect the bundle's task list against it. Tasks not in `allowed_tasks` are skipped entirely. Absent `allowed_tasks` = all tasks allowed.

## Execute

For each task in order:

1. Before starting each task: `git checkout <default-branch> && git pull` and confirm the working tree is clean. Each audit task creates its own branch + PR and must start from a clean base.
2. Fetch `https://raw.githubusercontent.com/frontkom/night-shift/main/tasks/<task-id>.md`.
3. Execute the task exactly as written.
4. Apply the bundle's rules from the manifest. Audits is `parallelism: independent`, `stop_on_failure: false` — one task failing or exiting must **not** stop the bundle.
5. If a task says "exit silently" (no real issues found, or a similar PR already open), continue with the next.

## Mode

Per the manifest, this bundle is **pull-request** mode. Each task creates its own feature branch and opens its own PR.
