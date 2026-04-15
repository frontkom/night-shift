# Implement Plans

Implement the next pending phase of **one** plan file and open a PR for it. One PR per plan. The multi-plans wrapper fans out — it dispatches one subagent per plan file, so every pending plan gets its own run and its own PR on the same night. **Never scan for or process plans beyond the one you were given.**

## Read project config first
Read `CLAUDE.md` for the **Night Shift Config** section (test command, build command, default branch, plans dir). If not present, use the defaults documented in `bundles/_multi-runner.md`.

**Allowlist check.** If the dispatcher passed an `allowed_tasks` list and `build-planned-features` is not in it, exit silently. Absent `allowed_tasks` = all tasks allowed (backward compatible).

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`), operate inside that app only:
- The plans directory is `<app_path>/<plans dir>` (default `<app_path>/docs`).
- All file paths referenced by the plan are interpreted relative to the repo root but must live under `<app_path>`. Skip plans that touch files outside `<app_path>`.
- Use the app-scoped test and build commands from the scoped config.
- The branch name includes the app slug: `nightshift/plan-<app-slug>-<plan-slug>-phase-<N>-YYYY-MM-DD` where `<app-slug>` is the last segment of `<app_path>` (e.g. `web` for `apps/web`).
- The PR title names the app: `nightshift/plan: <app_path> — <plan-name> phase <N>`.

When no `app_path` is provided (single-app repo), the plans directory defaults to `docs/` and branch / PR titles omit the app slug — the pre-monorepo behaviour.

## Steps
1. You were given a specific `PLAN_FILE` by the dispatcher. Read **only that file**. Do not list or scan the plans directory. If no `PLAN_FILE` was supplied (single-agent fallback, e.g. running this task directly on one repo), find a plan to work on:
   - Scan **all markdown files** in the plans directory (default `docs/`) and its subdirectories for plan documents (files containing phases, milestones, or implementation steps).
   - Look for files named `*-PLAN.md`, but also check other `.md` files that may contain implementation plans without following the naming convention.
   - Pick the first plan with a pending phase.

2. Read the plan file carefully. Identify all phases. A phase is "implemented" if it is explicitly marked as done/completed/implemented in the plan file, **or** if its referenced files / migrations / exports already exist with the described shape. Find the first pending phase.
   - **Skip plans that are fully implemented.** If every phase is marked as done or implemented, exit silently.
   - **Skip plans marked as deferred, blocked, or on hold.**

3. Implement exactly that one phase. One phase per plan per run — never advance two phases of the same plan in one run.

4. **Update the plan file.** After implementing a phase, mark it as completed in the plan file itself so the same phase is not re-implemented on subsequent runs. Use the plan's existing convention for marking completion (e.g. checkboxes `[x]`, strikethrough, "Status: Done", etc.). If no convention exists, add a line like `**Status: Implemented (YYYY-MM-DD)**` under the phase heading.

5. Check for an existing open PR for this plan + phase to avoid duplicates:
   ```
   gh pr list --search "nightshift/plan in:title" --state open --json title
   ```
   If a PR for the same plan + phase (and app, when scoped) is already open, exit silently.

6. Create a branch:
   ```
   # scoped:
   git checkout -b nightshift/plan-<app-slug>-<plan-slug>-phase-<N>-YYYY-MM-DD
   # unscoped:
   git checkout -b nightshift/plan-<plan-slug>-phase-<N>-YYYY-MM-DD
   ```
   `<plan-slug>` is the plan filename without `-PLAN.md` (or without `.md` for non-standard names).

7. Follow the plan's file paths and specs literally. Do not invent scope. When scoped, do not edit files outside `<app_path>`.

8. Run the **test command** and **build command** from the scoped config (or top-level config when unscoped). Both must pass.

9. If anything fails, do not commit. Leave a note in the plan file under a `## Night Shift Notes` section describing what blocked you, then commit only that note + push the branch + open the PR with a `[blocked]` prefix in the title so a human can pick it up.

## Open the PR
On success (drop the `<app_path> — ` prefix from commit + PR title when unscoped):
```
git add -A
git commit -m "nightshift(plan): <app_path> — <plan-name> phase <N> — <short title>"
git push -u origin HEAD
gh pr create --title "nightshift/plan: <app_path> — <plan-name> phase <N>" \
  --body "$(cat <<'EOF'
## Plan
<plan filename and link to docs/<plan>-PLAN.md>

## Phase
<which phase, what it covers>

## Changes
- <bullets per file touched>

## Plan file updated
- Marked phase <N> as implemented in <plan filename>

## Verification
- test command output: pass
- build command output: pass

## Next phase
<short note on what would be next so the human reviewer knows the trajectory>
EOF
)"
```

## Idempotency
- One phase per plan per run. Never advance two phases of the same plan in one run. Different plans run in different subagents and each get their own PR on the same night — that is the intended behaviour.
- If the supplied `PLAN_FILE` has no pending phases, exit silently.
- If a PR for the same plan + phase (+ app, when scoped) is already open, exit silently — do not stack.
- Always update the plan file to mark completed phases — this is what prevents re-running the same work.
