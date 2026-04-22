# Implement Plans

Implement as many pending phases of **one** plan file as you reasonably can, bundled into a **single PR**. One PR per plan, per run. The multi-plans wrapper fans out — it dispatches one subagent per plan file, so every pending plan gets its own run and its own PR on the same night. **Never scan for or process plans beyond the one you were given.**

**How far to go in one run.** Keep implementing pending phases sequentially until one of the following is true:
- Every phase of the plan is done (you're completing the plan — include the plan deletion in this PR).
- The next phase fails tests, build, or reveals a blocker (stop, keep the passing phases, note the blocker).
- The next phase cannot be started without feedback from review of earlier phases (e.g. its design depends on a decision the previous phase surfaced).
- The diff is growing large enough that reviewability is degrading. Rough heuristic: stop before a single PR touches more than ~15 files or ~600 added lines, unless the phases are trivially repetitive.
- You are approaching the limits of your own context window and want to leave headroom for test runs and PR assembly.

Use your judgement — the goal is the fewest PRs that still review cleanly. A two-phase plan should usually land as one PR; a ten-phase plan will likely land as two or three.

## Read project config first
Read `CLAUDE.md` for the **Night Shift Config** section (test command, build command, default branch, plans dir). If not present, use the defaults documented in `bundles/_multi-runner.md`.

**Allowlist check.** If the dispatcher passed an `allowed_tasks` list and `build-planned-features` is not in it, exit silently. Absent `allowed_tasks` = all tasks allowed (backward compatible).

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`), operate inside that app only:
- The plans directory is `<app_path>/<plans dir>` (default `<app_path>/docs`).
- All file paths referenced by the plan are interpreted relative to the repo root but must live under `<app_path>`. Skip plans that touch files outside `<app_path>`.
- Use the app-scoped test and build commands from the scoped config.
- The branch name includes the app slug: `nightshift/plan-<app-slug>-<plan-slug>-YYYY-MM-DD` where `<app-slug>` is the last segment of `<app_path>` (e.g. `web` for `apps/web`).
- The PR title names the app: `nightshift/plan: <app_path> — <plan-name> <phase-range>` where `<phase-range>` is e.g. `phase 2`, `phases 2–4`, or `(completes plan)` if every remaining phase landed.

When no `app_path` is provided (single-app repo), the plans directory defaults to `docs/` and branch / PR titles omit the app slug — the pre-monorepo behaviour.

## Steps
1. You were given a specific `PLAN_FILE` by the dispatcher. Read **only that file**. Do not list or scan the plans directory. If no `PLAN_FILE` was supplied (single-agent fallback, e.g. running this task directly on one repo), find a plan to work on:
   - Discover plan files using the same conventions the wrapper uses — see `bundles/multi-plans.md` → "list plan files":
     - `*-PLAN.md` (suffix), `PLAN-*.md` (prefix), `*.plan.md` (dotted), and any `.md` file inside a `plans/` subdirectory.
   - Pick the first plan with a pending unit (phase / item / step / milestone). See step 3 for what counts as a unit.

2. Read the plan file carefully. Identify all phases. A phase is "implemented" if it is explicitly marked as done/completed/implemented in the plan file, **or** if its referenced files / migrations / exports already exist with the described shape. Build the ordered list of pending phases.
   - **Skip plans that are fully implemented.** If every phase is marked as done or implemented, exit silently.
   - **Skip plans marked as deferred, blocked, or on hold.**

3. Implement pending phases sequentially, in plan order. One PR will bundle all phases you land in this run.

   What counts as a "phase" depends on the plan's structure:
   - **Numbered phases** (`## Phase 1`, `## Phase 2`, …).
   - **Priority/checklist tables** (`| 1 | Item A | … |`, `- [ ] Item B`, etc.) — each row/checkbox is one phase.
   - **Step-by-step lists** (`### Step 1`, `### Step 2`, …).
   - **Free-form milestones** (`## Milestone: …`).

   Between phases, run the test command and build command (see step 8). If either fails, **stop** — keep the phases that passed, revert the failing phase's changes, record the blocker in the plan file under `## Night Shift Notes`, and proceed to open the PR with what you have.

   The PR title and body MUST name the exact phase range landed (e.g. `phases 2–4`, or `phase 2` if only one phase fit). Never obscure the range behind a generic title.

4. **Update the plan file.** For every phase you landed, mark it as completed in the plan file so future runs don't re-implement it. Use the plan's existing convention (checkboxes `[x]`, strikethrough, `**Status: Done**`, etc.). If no convention exists, add a line like `**Status: Implemented (YYYY-MM-DD)**` under each completed phase heading.

4b. **If the phases you landed were the last pending ones, delete the plan file in the same PR.** Re-scan the plan after marking step 4: if **zero** pending phases remain, the plan has served its purpose. Use `git rm <plan-file>` so the deletion is part of the PR diff, and suffix the PR title with ` (completes plan)`. The plan's history stays in git — what we lose from the live `docs/` tree is the noise of completed roadmaps, not the historical record.

   **Opt-out** — if the plan file contains the literal string `nightshift: keep` anywhere (front matter, an HTML comment like `<!-- nightshift: keep -->`, or a `Status:` line such as `**Status: Complete (keep as reference)**`), do **not** delete it. The user wants that plan preserved as a live reference. Mark it as `**Status: Implemented (YYYY-MM-DD)**` and leave the file in place; future wrapper pre-filters will record it as `not-applicable` indefinitely without dispatching a subagent.

   **Migration tip for plans that contain non-roadmap material:** if the plan file has design rationale, alternatives-considered, or other reference material the team wants to keep beyond implementation, move that material to an ADR (`docs/adr/NNNN-<slug>.md`) **before** the final unit lands. The plan file then truly only contains roadmap and can be safely deleted.

5. Check for an existing open PR for this plan to avoid duplicates:
   ```
   gh pr list --search "nightshift/plan in:title" --state open --json title
   ```
   If **any** open PR already exists for this plan (and app, when scoped) — regardless of which phases it covers — exit silently. Stacking multiple open PRs for one plan creates merge-order ambiguity for the human reviewer; wait for the existing one to merge or close.

6. Create a branch:
   ```
   # scoped:
   git checkout -b nightshift/plan-<app-slug>-<plan-slug>-YYYY-MM-DD
   # unscoped:
   git checkout -b nightshift/plan-<plan-slug>-YYYY-MM-DD
   ```
   `<plan-slug>` is the plan filename without `-PLAN.md` (or without `.md` for non-standard names).

7. Follow the plan's file paths and specs literally. Do not invent scope. When scoped, do not edit files outside `<app_path>`.

8. Run the **test command** and **build command** from the scoped config (or top-level config when unscoped) after each phase you complete. Both must pass before moving on to the next phase. Re-run them once more after the final phase in this run.

9. If anything fails on the **first phase you attempt**, do not commit — leave a note in the plan file under a `## Night Shift Notes` section describing what blocked you, then commit only that note + push the branch + open the PR with a `[blocked]` prefix in the title so a human can pick it up.

   If a later phase fails after earlier phases in this run already passed, **keep the earlier phases**. Revert only the failing phase's changes (`git checkout -- <files>` or reset the staged portion), add a `## Night Shift Notes` entry to the plan file explaining the blocker on phase N+K, and proceed to open the PR covering phases 1…N+K-1 normally. This gets the passing work reviewed promptly and surfaces the blocker to the human.

## Open the PR
On success (drop the `<app_path> — ` prefix from commit + PR title when unscoped). The wrapper has already created the standard labels for this repo — just attach them. End the body with the Night Shift footer:
```
git add -A
git commit -m "nightshift(plan): <app_path> — <plan-name> <phase-range> — <short title>"
git push -u origin HEAD

cat > /tmp/nightshift-pr-body.md <<'EOF'
## Plain summary
<1-2 sentences in English (PR review is always in English, regardless of the product's user language). What capability is now available to which users — the feature in their words, not the implementation. Skip plan-doc references and file paths here. See bundles/_multi-runner.md → "Body header — Plain summary".>

## Plan
<plan filename and link to docs/<plan>-PLAN.md>

## Phases landed in this PR
- Phase <N>: <one-line summary of what it covers>
- Phase <N+1>: <…>
- <… one bullet per phase included in this PR>

## Changes
- <bullets per file touched>

## Plan file updated
- Marked phases <N>–<M> as implemented in <plan filename>
- <if plan is now complete: "Deleted <plan filename> — plan complete; history preserved in git">

## Verification
- test command output: pass (run after each phase)
- build command output: pass (run after each phase)

## Remaining work
<short note on what phases remain and what would be picked up next night; for a completing PR write "None — this PR completes the plan and removes <plan filename>."; if an attempted phase was blocked, describe the blocker and reference the `## Night Shift Notes` entry in the plan file.>

---
_Run by Night Shift • plans/build-planned-features_
EOF

# Normal PR (more phases still pending):
gh pr create --title "nightshift/plan: <app_path> — <plan-name> <phase-range>" \
  --label nightshift --label "nightshift:plans" \
  --body-file /tmp/nightshift-pr-body.md
# Completes-the-plan variant:
# gh pr create --title "nightshift/plan: <app_path> — <plan-name> <phase-range> (completes plan)" \
#   --label nightshift --label "nightshift:plans" \
#   --body-file /tmp/nightshift-pr-body.md
```

**Always use `--body-file`, never inline `--body`.** Inline body strings get silently flattened to one-liners with literal `\n` — the entire PR body then renders as one unbroken paragraph on GitHub. See `bundles/_multi-runner.md` → "PR body formatting".

**Do not** modify `docs/NIGHTSHIFT-HISTORY.md` from this branch — the multi-runner wrapper appends the history row on `main` after you return your one-line result.

## Idempotency
- One PR per plan per run. Implement as many pending phases as reasonably fit (see "How far to go in one run" at the top). Different plans run in different subagents and each get their own PR on the same night — that is the intended behaviour.
- If the supplied `PLAN_FILE` has no pending units, exit silently.
- If a PR for the same plan (+ app, when scoped) is already open — covering any phase range — exit silently. Do not stack a second open PR for the same plan.
- Always update the plan file to mark every phase you completed — this is what prevents re-running the same work next night.
- When the phases you implement include the **last** pending one, also `git rm` the plan file in the same PR — unless the plan opts out via `nightshift: keep`. The completed-plan deletion is part of the unit-completion contract, not a separate cleanup step.
