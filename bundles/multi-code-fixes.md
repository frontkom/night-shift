# Multi-repo: Code fixes

You are running the Night Shift **Code fixes** bundle across **all target repositories** cloned into this session.

**Before doing anything else**, print a single status line so the user sees immediate output:
`Night Shift code-fixes bundle starting (multi-repo)...`

## Discover repos
List sibling directories at the top of your working tree. For each candidate, confirm via `git rev-parse --show-toplevel`.

## Per-repo loop — isolated subagent per repo

For each discovered target repo, in directory-name order:

1. From the main wrapper, briefly `cd` into the repo to:
   - `git status --porcelain` — if dirty, record `dirty-skip` and continue.
   - Check opt-out signals (`.nightshift-skip`, or `Night Shift: skip` in `CLAUDE.md` / `AGENTS.md` / `README.md`). Record `opted-out` and continue if any are present.
   - Capture the absolute repo path. `cd` back to the parent.
2. Dispatch a `Task` subagent with this prompt (substitute `{REPO_PATH}`):

   ```
   Your working directory is {REPO_PATH}. cd into it now.

   Fetch https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/code-fixes.md
   and execute it against this repository. The bundle runs add-tests → improve-accessibility
   → translate-ui strictly in order, stopping per-repo on a failed test or build.

   CLAUDE.md is optional. Honor `## Night Shift Config` if present, otherwise apply
   the defaults from
   https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/_multi-runner.md.

   At the end of your run, append ONE LINE to docs/NIGHTSHIFT-HISTORY.md (create the
   file if missing) under the `## Runs` heading at the top of the runs list. Format:
       - YYYY-MM-DD code-fixes <app_path or —>  <ok|silent|failed>  <terse note, max 80 chars>
   Then commit + push the history file.

   Return EXACTLY ONE LINE to me in this format:
       <ok|silent|failed> | <terse note, max 80 chars>
   ```
3. Capture only the one-line result. Do not echo subagent work into your own context.
4. Move on to the next repo.

If a subagent dispatch itself fails, record `failed | dispatch error: <reason>`.

## Final report
Print this summary table and stop. The summary table is the primary artifact — it appears in the trigger dashboard. **Do not** write the summary to any external repo; the per-repo `docs/NIGHTSHIFT-HISTORY.md` files in each target repo are the only persisted history.

```
Night Shift code-fixes — multi-repo summary

| Repo | Status | Notes |
|------|--------|-------|
| ...  | ok / silent / opted-out / dirty-skip / failed | <terse> |
```
