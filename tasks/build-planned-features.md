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
   - Discover plan files using the same conventions the wrapper uses — see `bundles/multi-plans.md` → "list plan files":
     - `*-PLAN.md` (suffix), `PLAN-*.md` (prefix), `*.plan.md` (dotted), and any `.md` file inside a `plans/` subdirectory.
   - Pick the first plan with a pending unit (phase / item / step / milestone). See step 3 for what counts as a unit.

2. Read the plan file carefully. Identify all phases. A phase is "implemented" if it is explicitly marked as done/completed/implemented in the plan file, **or** if its referenced files / migrations / exports already exist with the described shape. Find the first pending phase.
   - **Skip plans that are fully implemented.** If every phase is marked as done or implemented, exit silently.
   - **Skip plans marked as deferred, blocked, or on hold.**

3. Implement exactly that one **unit of work**. One unit per plan per run — never combine multiple units in one PR.

   What counts as "one unit" depends on the plan's structure:
   - **Numbered phases** (`## Phase 1`, `## Phase 2`, …) → exactly one phase per run.
   - **Priority/checklist tables** (`| 1 | Item A | … |`, `- [ ] Item B`, etc.) → exactly one item per run.
   - **Step-by-step lists** (`### Step 1`, `### Step 2`, …) → exactly one step per run.
   - **Free-form milestones** (`## Milestone: …`) → exactly one milestone per run.

   The branch name and PR title MUST identify that single unit. **Never** title a PR `phase 7+13`, `items 1 and 4`, `steps 2,3,5`, or any combination form. If you find yourself wanting to bundle two units because they're "obviously related," resist — file them as two separate PRs on consecutive nights so a reviewer can accept or reject each independently. The plan agent fans out one subagent per plan, not per unit, so the next unit will be picked up the very next night anyway.

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
On success (drop the `<app_path> — ` prefix from commit + PR title when unscoped). The wrapper has already created the standard labels for this repo — just attach them. End the body with the Night Shift footer:
```
git add -A
git commit -m "nightshift(plan): <app_path> — <plan-name> phase <N> — <short title>"
git push -u origin HEAD

cat > /tmp/nightshift-pr-body.md <<'EOF'
## Plain summary
<1-2 sentences in English (PR review is always in English, regardless of the product's user language). What capability is now available to which users — the feature in their words, not the implementation. Skip plan-doc references and file paths here. See bundles/_multi-runner.md → "Body header — Plain summary".>

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

---
_Run by Night Shift • plans/build-planned-features_
EOF

gh pr create --title "nightshift/plan: <app_path> — <plan-name> phase <N>" \
  --label nightshift --label "nightshift:plans" \
  --body-file /tmp/nightshift-pr-body.md
```

**Always use `--body-file`, never inline `--body`.** Inline body strings get silently flattened to one-liners with literal `\n` — the entire PR body then renders as one unbroken paragraph on GitHub. See `bundles/_multi-runner.md` → "PR body formatting".

**Do not** modify `docs/NIGHTSHIFT-HISTORY.md` from this branch — the multi-runner wrapper appends the history row on `main` after you return your one-line result.

## Idempotency
- One unit of work per plan per run (one phase, one item, one step, one milestone — see step 3 for the definitions). Never combine units in one PR. Different plans run in different subagents and each get their own PR on the same night — that is the intended behaviour.
- If the supplied `PLAN_FILE` has no pending units, exit silently.
- If a PR for the same plan + unit (+ app, when scoped) is already open, exit silently — do not stack.
- Always update the plan file to mark completed units — this is what prevents re-running the same work.
