# Multi-repo: Docs

You are running the Night Shift **Docs** bundle across **all target repositories** cloned into this session.

**Before doing anything else**, print a single status line so the user sees immediate output:
`Night Shift docs bundle starting (multi-repo)...`

## Discover repos
List sibling directories at the top of your working tree. For each candidate, confirm via `git rev-parse --show-toplevel`.

## Per-repo loop — isolated subagent per repo

For each discovered target repo, in directory-name order:

1. From the main wrapper, briefly `cd` into the repo to:
   - `git status --porcelain` — if dirty, record `dirty-skip` and continue.
   - Check opt-out signals (`.nightshift-skip`, or `Night Shift: skip` in `CLAUDE.md` / `AGENTS.md` / `README.md`). Record `opted-out` and continue if any are present.
   - **Ensure all five Night Shift labels exist on the repo** (idempotent — silent if they already exist). Run this once per repo before dispatching subagents:
     ```
     gh label create night-shift --color "0e8a16" --description "Automated by Night Shift" 2>/dev/null || true
     gh label create "night-shift:plans" --color "1d76db" --description "Night Shift plans bundle" 2>/dev/null || true
     gh label create "night-shift:docs" --color "1d76db" --description "Night Shift docs bundle" 2>/dev/null || true
     gh label create "night-shift:code-fixes" --color "1d76db" --description "Night Shift code-fixes bundle" 2>/dev/null || true
     gh label create "night-shift:audits" --color "1d76db" --description "Night Shift audits bundle" 2>/dev/null || true
     ```
     All five are created together so subagents in any future bundle can rely on them. See `bundles/_multi-runner.md` → "Labels (created at wrapper level, applied at task level)".
   - Capture the absolute repo path. `cd` back to the parent.
2. Dispatch a `Task` subagent with this prompt (substitute `{REPO_PATH}`):

   ```
   Your working directory is {REPO_PATH}. cd into it now.

   Fetch https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/docs.md
   and execute it against this repository. The bundle runs the four doc tasks
   (update-changelog, update-user-guide, document-decisions, suggest-improvements).

   CLAUDE.md is optional. Honor `## Night Shift Config` if present, otherwise apply
   the defaults from
   https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/_multi-runner.md.

   Return EXACTLY ONE LINE to me in this format:
       <ok|silent|failed> | PRs: <comma-separated urls or —> | <terse note, max 80 chars>
   ```
3. Capture only the one-line result. Do not echo subagent work into your own context.
4. Move on to the next repo.

If a subagent dispatch itself fails, record `failed | dispatch error: <reason>` in the summary.

## Final report
Print this summary table and stop. The summary table is the primary artifact — it appears in the routines dashboard. The per-repo PR list (`gh pr list --label night-shift:docs`) is the persisted audit trail.

```
Night Shift docs — multi-repo summary

| Repo | Status | Notes |
|------|--------|-------|
| ...  | ok / silent / opted-out / dirty-skip / failed | <terse> |
```
