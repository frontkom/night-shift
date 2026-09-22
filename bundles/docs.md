# Docs bundle

**Model and effort:** Run this bundle and every nested task/subagent with **Claude Opus 5** (`claude-opus-5`) at **medium effort** (`medium`). Inherit these settings from a verified parent or set them explicitly through supported runtime controls. Do not downgrade models or increase effort. Prompt text alone does not configure the runtime; if these settings cannot be verified, report the blocker before dispatching work. See `skills/night-shift/SKILL.md` → **Model and effort** for setup and migration.

You are running the Night Shift **Docs** bundle on this repository.

**Before doing anything else**, print a single status line so the user sees immediate output:
`Night Shift docs bundle starting on <repo-name>...`

## Setup
Read `CLAUDE.md` for the **Night Shift Config** section if present. If absent, use defaults — see `_multi-runner.md`.

## Resolve tasks from manifest

Fetch and parse https://raw.githubusercontent.com/frontkom/night-shift/main/manifest.yml.

- Read `bundles.docs` for this bundle's settings.
- Read `tasks[]` and select all entries where `bundle: docs`. Sort by `order` ascending. This is the canonical task list — **do not** rely on a hardcoded list anywhere else.
- **Allowlist filter.** If the dispatcher passed `allowed_tasks` (a list of task ids), intersect the bundle's task list against it. Tasks not in `allowed_tasks` are skipped entirely. Absent `allowed_tasks` = all tasks allowed.

## Execute

For each task in order:

1. Fetch `https://raw.githubusercontent.com/frontkom/night-shift/main/tasks/<task-id>.md`.
2. Execute the task exactly as written, including its commit and push steps.
3. Apply the bundle's rules from the manifest. Docs is `parallelism: independent`, `stop_on_failure: false` — one task's exit must not affect the others.
4. If a task says "exit silently", that is success — continue with the next.

## Mode

Per the manifest, this bundle is **pull-request** mode. Each task creates a feature branch and opens a PR for review.
