# Multi-repo: CI failure triage

You are running the Night Shift **Triage CI failures** bundle across **all target repositories** cloned into this session.

**Before doing anything else**, print a single status line so the user sees immediate output:
`Night Shift triage-ci bundle starting (multi-repo)...`

## Discover repos
List sibling directories at the top of your working tree. For each candidate, confirm via `git rev-parse --show-toplevel`.

## Per-repo loop — isolated subagent per repo

For each discovered target repo, in directory-name order:

1. From the main wrapper, briefly `cd` into the repo to:
   - `git status --porcelain` — if dirty, this task does not edit code, so no skip is needed; proceed.
   - Check opt-out signals (`.nightshift-skip`, or `Night Shift: skip` in `CLAUDE.md` / `AGENTS.md` / `README.md`). Record `opted-out` and continue if any are present.
   - Capture the absolute repo path. `cd` back to the parent.
2. Dispatch a `Task` subagent with this prompt (substitute `{REPO_PATH}`):

   ```
   Your working directory is {REPO_PATH}. cd into it now.

   Fetch https://raw.githubusercontent.com/frontkom/night-shift/main/tasks/triage-ci-failures.md
   and execute it against this repository. The task triages every open Night Shift
   PR's failed and cancelled CI checks: it posts an explanatory comment per
   failure, re-runs cancellations and clearly-unrelated failures, and leaves
   real-looking failures alone for a human to review.

   The task does NOT open new PRs or push commits — it only comments on existing
   PRs and re-runs CI workflows.

   CLAUDE.md is optional. Honor `## Night Shift Config` if present, otherwise apply
   the defaults from
   https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/_multi-runner.md.

   Return EXACTLY ONE LINE to me in this format:
       <ok|silent|failed> | triaged: <N> PRs, <C> comments posted, <R> reruns triggered | <terse note>
   ```
3. Capture only the one-line result. Do not echo subagent work into your own context.
4. Move on to the next repo.

If a subagent dispatch itself fails, record `failed | dispatch error: <reason>` in the summary.

## No PR sweeps for this bundle

Unlike the other multi-* wrappers, this bundle does **not** run the label sweep or PR body sweep. Reason: triage-ci does not create new PRs — it only comments on existing ones — so there is nothing for those sweeps to repair. Skipping them keeps the routine fast and avoids redundant work the other bundles already did earlier in the night.

## Final report

Print this summary table and stop. The summary table is the primary artifact — it appears in the routines dashboard. The audit trail lives on the PRs themselves: filter `gh pr list --label night-shift --state open` and look for the `night-shift-triage:` HTML markers in PR comments to see which checks have been triaged on which run.

```
Night Shift triage-ci — multi-repo summary

| Repo | Status | Triaged | Comments | Reruns | Notes |
|------|--------|---------|----------|--------|-------|
| ...  | ok / silent / opted-out / failed | <N PRs> | <C> | <R> | <terse> |
```

Status values: `ok` (at least one comment or rerun happened), `silent` (no open Night Shift PRs to triage, or all already-triaged), `opted-out`, `failed`. Keep notes terse. No further prose after the table.
