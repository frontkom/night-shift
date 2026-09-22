# Plans bundle

**Model and effort:** Run this bundle and every nested task/subagent with **Claude Opus 5** (`claude-opus-5`) at **medium effort** (`medium`). Inherit these settings from a verified parent or set them explicitly through supported runtime controls. Do not downgrade models or increase effort. Prompt text alone does not configure the runtime; if these settings cannot be verified, report the blocker before dispatching work. See `skills/night-shift/SKILL.md` → **Model and effort** for setup and migration.

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

## Self-review

After each task's post-create ritual finishes, run the **Self-review + one revision** step from `_multi-runner.md` before returning. One review, at most one revision commit, same branch. If the revision breaks tests, revert with `--force-with-lease` and keep the original PR.
