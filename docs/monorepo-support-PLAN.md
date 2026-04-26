# Monorepo support — PLAN

Make Night Shift behave correctly in repos that contain multiple apps
(e.g. a Turborepo with several Next.js apps under `apps/*`). Today the unit
of work is one repo, with a single `test command`, `build command`, and
`key pages` list — which collapses incorrectly when a repo holds multiple
apps owned by different reviewers.

The goal is **per-app scoping inside a repo**, opt-in via config, with no
behaviour change for single-app repos.

## Phase 1 — Config schema for apps

Extend the **Night Shift Config** section in a project's `CLAUDE.md` with an
optional `apps:` list. When `apps:` is absent, everything works exactly as
today (single-app mode).

**Files to touch**

- `HOW-TO.md` — document the new `apps:` block under "Configure a project".
- `bundles/_multi-runner.md` — describe how a Task subagent should resolve
  config: prefer the matching `apps[].path` block when running scoped to an
  app, fall back to the top-level keys otherwise.

**Schema (documented in HOW-TO.md):**

```yaml
# Night Shift Config
default branch: main
push protocol: pr
doc language: en

apps:
  - path: apps/web
    test: pnpm --filter web test
    build: pnpm --filter web build
    key pages:
      - apps/web/app/page.tsx
      - apps/web/app/(marketing)/pricing/page.tsx
    plans dir: apps/web/docs
  - path: apps/admin
    test: pnpm --filter admin test
    build: pnpm --filter admin build
    key pages:
      - apps/admin/app/dashboard/page.tsx
```

**Acceptance**

- A repo with no `apps:` block is unaffected.
- The schema is documented in `HOW-TO.md` with one full example.
- `bundles/_multi-runner.md` explains the resolution rule clearly enough
  that any task author can follow it.

## Phase 2 — Per-app dispatch in the multi-runner

Teach the multi-* wrappers to expand "one task subagent per repo" into
"one task subagent per (repo, app)" when a repo declares `apps:`.

**Files to touch**

- `bundles/_multi-runner.md` — add a "discovery" step: after cloning a
  repo, parse its `CLAUDE.md` Night Shift Config; if `apps:` exists, emit
  one work-item per app, otherwise one work-item for the whole repo. Each
  work-item carries `{repo, app_path | null, scoped_config}`.
- `bundles/multi-plans.md` — pass the work-item's `app_path` and scoped
  config to the dispatched `build-planned-features` subagent.
- `bundles/multi-docs-and-code-fixes.md` — same, for the docs + code-fixes
  bundle.
- `bundles/multi-audits.md` — same, for the audits bundle.

**Acceptance**

- A monorepo with two `apps:` entries spawns two task subagents per task,
  not one.
- A single-app repo (no `apps:` block) still spawns exactly one subagent
  per task — no double work.
- The summary table prints one row per (repo, app) when scoped, one row
  per repo otherwise.

## Phase 3 — Task-side scoping

Each task that currently reads `key pages`, `test command`, `build
command`, or scans the repo tree must learn to operate inside `app_path`
when one is provided.

**Files to touch (one phase entry per task to keep PRs focused)**

- `tasks/build-planned-features.md` — read plans from `<app_path>/<plans
  dir>` instead of `docs/`. Branch name includes the app slug
  (`night-shift/plan-web-<plan>-phase-N-...`). **Each plan execution gets
  its own PR** — one PR per plan touched, never bundled. Relax the global
  "one phase per night, ever" cap to "one phase per plan per night": in a
  monorepo, two different plans (in different apps, or even the same app)
  can each land a phase on the same night, but any single plan still
  advances at most one phase per run.
- `tasks/add-tests.md` — only walk files under `app_path`. Run the
  scoped test command.
- `tasks/find-bugs.md` — same scoping.
- `tasks/find-security-issues.md` — same scoping. Note: keep secret
  scanning repo-wide; only the code review is per-app.
- `tasks/improve-performance.md` — read `key pages` from the scoped
  config. PR title includes the app name.
- `tasks/improve-seo.md` — same.
- `tasks/improve-accessibility.md` — same.
- `tasks/translate-ui.md` — translation files are usually per-app; resolve
  paths under `app_path` first.
- `tasks/update-changelog.md` — write to `<app_path>/CHANGELOG.md` when
  scoped, fall back to repo-root `CHANGELOG.md` otherwise.
- `tasks/update-user-guide.md` — same fallback rule for the user guide.
- `tasks/document-decisions.md` — ADRs stay repo-wide. This task ignores
  app scoping and only runs once per repo even when `apps:` is set. The
  multi-runner needs a way to mark a task as "repo-scoped only" — see
  Phase 4.
- `tasks/suggest-improvements.md` — repo-wide, same exception as ADR.

**Acceptance**

- Each task either operates inside `app_path` or is explicitly marked
  repo-scoped.
- A monorepo run produces PRs whose titles name the app
  (`night-shift(perf): apps/web — LCP fixes`), so reviewers know which
  team owns the change.
- Single-app repos see no change in PR titles or behaviour.

## Phase 4 — "Repo-scoped only" task marker

Some tasks (ADRs, repo-wide suggestions, secret scans) shouldn't be
duplicated per app. Add a small mechanism so the multi-runner knows to
collapse them back to one work-item per repo even when `apps:` is set.

**Files to touch**

- `manifest.yml` — add a `scope: repo | app` field to each task entry.
  Default `app`. Mark `document-decisions` and `suggest-improvements` as
  `scope: repo`. (Find-security-issues stays `scope: app` for the code
  review part — secret scanning happens at the repo level via a separate
  pre-step in `find-security-issues.md`.)
- `bundles/_multi-runner.md` — when expanding work-items, consult
  `manifest.yml` and skip the per-app fan-out for `scope: repo` tasks.
- `HOW-TO.md` — note the new field briefly so external readers
  understand why some tasks fan out and others don't.

**Acceptance**

- ADRs and suggestions run exactly once per repo regardless of `apps:`.
- The manifest is the single source of truth for task scoping.

## Phase 5 — Smoke test on a real monorepo

Validate the whole chain end-to-end on one real Turborepo before declaring
victory.

**Files to touch**

- `docs/ideas/slack-reporting.md` — update the example digest layout to
  show app-scoped lines, since this affects how the future Slack report
  should group findings.

**Acceptance**

- A test run against a Turborepo with two Next.js apps produces:
  - Two PRs from `improve-performance` (one per app).
  - One PR from `document-decisions` (repo-wide).
  - PR titles that name the app for `scope: app` tasks and omit it for `scope: repo` tasks.
- A test run against a single-app repo produces output identical to
  pre-change behaviour (no spurious second subagent, no app names in PR
  titles).

## Out of scope

- Auto-detecting apps from the filesystem (`apps/*`, `packages/*`). Too
  brittle, and the config is cheap to write. Always explicit.
- Per-app `.nightshift-skip`. The repo-level skip file is enough for now;
  if a single app is broken, exclude it from the `apps:` list.
- Multi-language monorepos (Next.js + a Python service). Same mechanism
  should work, but the smoke test in Phase 5 only validates Next.js.
