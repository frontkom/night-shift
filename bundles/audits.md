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

## Branch and PR naming — read the slug from `manifest.yml`

Every pull-request task in `manifest.yml` declares its own `slug:` field. That field is the **single source of truth** for branch names and PR-title prefixes. **Use it — never the raw task id.** For the audits bundle the values today are (cross-check `manifest.yml` if this list ever feels stale):

| Task id (as in `manifest.yml`) | `slug:` field |
|---|---|
| `find-security-issues` | `security` |
| `find-bugs` | `bug` |
| `improve-seo` | `seo` |
| `improve-performance` | `perf` |
| `dep-audit` | `deps` |

A branch must therefore look like `night-shift/perf-YYYY-MM-DD` or `night-shift/perf-<app-slug>-YYYY-MM-DD` — **not** `night-shift/improve-performance`. The PR title must start with `night-shift/<slug>:` (e.g. `night-shift/perf: …`), **not** `night-shift/improve-performance: …`. The post-create ritual's title-format check (`_multi-runner.md`) will warn if you used the task id instead of the slug; re-run `gh pr edit --title` to fix before returning.

This same rule applies recursively to anything calling subagents from inside this bundle — pass the **task id** through `allowed_tasks`, but read the slug from `manifest.yml` (or the task file's branch-naming example) before naming branches or PR titles.

## Self-review

After each task's post-create ritual finishes, run the **Self-review + one revision** step from `_multi-runner.md` before returning. One review, at most one revision commit, same branch. If the revision breaks tests, revert with `--force-with-lease` and keep the original PR. Any code change carries some risk — audits introduce code (fixes + regression tests), so they get the same self-review pass as `plans` and `code-fixes`.
