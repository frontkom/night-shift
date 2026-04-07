# Task 00 — Implement Plans

Scan `docs/` for plan files matching `*-PLAN.md`. If any contain unimplemented phases with concrete file paths and code specs, implement the **next pending phase only** and open it as a PR (one PR per plan touched).

## Read project config first
Read `CLAUDE.md` for the **Night Shift Config** section (test command, build command, default branch). If not present, use the defaults documented in `bundles/_multi-runner.md`. If task 0 is explicitly excluded by the config, exit silently.

## Steps
1. List `docs/*-PLAN.md`. Skip plans marked **deferred**, **blocked**, or **on hold**.
2. For each remaining plan, identify phases. A phase is "implemented" if its referenced files / migrations / exports already exist with the described shape. Skip phases already done.
3. Pick the **first** plan with a pending phase. Implement only that one phase tonight. (One phase per night, ever — never two in one run.)
4. Check for an existing open PR for this plan to avoid duplicates:
   ```
   gh pr list --search "nightshift/plan in:title" --state open --json title
   ```
   If a PR for the same plan + phase is already open, exit silently.
5. Create a branch:
   ```
   git checkout -b nightshift/plan-<plan-slug>-phase-<N>-YYYY-MM-DD
   ```
   `<plan-slug>` is the plan filename without `-PLAN.md`.
6. Follow the plan's file paths and specs literally. Do not invent scope.
7. Run the project's **test command** and **build command**. Both must pass.
8. If anything fails, do not commit. Leave a note in the plan file under a `## Night Shift Notes` section describing what blocked you, then commit only that note + push the branch + open the PR with a `[blocked]` prefix in the title so a human can pick it up.

## Open the PR
On success:
```
git add -A
git commit -m "nightshift(plan): <plan-name> phase <N> — <short title>"
git push -u origin HEAD
gh pr create --title "nightshift/plan: <plan-name> phase <N>" \
  --body "$(cat <<'EOF'
## Plan
<plan filename and link to docs/<plan>-PLAN.md>

## Phase
<which phase, what it covers>

## Changes
- <bullets per file touched>

## Verification
- test command output: pass
- build command output: pass

## Next phase
<short note on what would be next so the human reviewer knows the trajectory>
EOF
)"
```

## Idempotency
- One phase per night, ever. Never implement two phases in one run, even across different plans.
- If no pending phases exist across all plans, exit silently.
- If a PR for the same plan + phase is already open, exit silently — do not stack.
