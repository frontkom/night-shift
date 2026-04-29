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
   - **Ensure the `night-shift` label exists on the repo** (idempotent — silent if it already exists). Run this once per repo before dispatching subagents:
     ```
     gh label create night-shift --color "0e8a16" --description "Automated by Night Shift" 2>/dev/null || true
     ```
     See `bundles/_multi-runner.md` → "Labels (created at wrapper level, applied at task level)".
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

   Return EXACTLY ONE LINE to me in this format:
       <ok|silent|failed> | PR: <url or —> | <terse note, max 80 chars>
   ```
3. Capture only the one-line result. Do not echo subagent work into your own context.
4. Run the **PR body sweep** in this repo as a wrapper-level safety net for subagents that skipped their per-task post-create ritual. Idempotent — only modifies bodies that contain literal `\n` sequences:

   ```bash
   ( cd "$REPO_PATH" && \
     for pr in $(gh pr list --label night-shift --state open --json number --jq '.[].number'); do
       body=$(gh pr view "$pr" --json body -q .body)
       case "$body" in
         *'\n'*)
           printf '%s' "$body" | python3 -c "import sys;sys.stdout.write(sys.stdin.read().replace(chr(92)+chr(110),chr(10)))" > /tmp/night-shift-body-fix.md
           gh pr edit "$pr" --body-file /tmp/night-shift-body-fix.md
           ;;
       esac
     done )
   ```
5. Move on to the next repo.

If a subagent dispatch itself fails, record `failed | dispatch error: <reason>` in the summary.

## Final report
Print this summary table and stop. The summary table is the primary artifact — it appears in the routines dashboard. The per-repo PR list (`gh pr list --label night-shift`) is the persisted audit trail; filter by title prefix (`night-shift/a11y:`, `night-shift/i18n:`, `night-shift/tests:`) to narrow to this bundle.

```
Night Shift code-fixes — multi-repo summary

| Repo | Status | Notes |
|------|--------|-------|
| ...  | ok / silent / opted-out / dirty-skip / failed | <terse> |
```
