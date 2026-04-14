# All bundles (single repo)

You are running **all four** Night Shift bundles against this single repository, in order. This is the one-shot "try Night Shift" entry point — no scheduling, no multi-repo, just run everything once against the current repo.

**Before doing anything else**, print a single status line so the user sees immediate output:
`Night Shift starting all bundles on <repo-name>...`

## Setup
Read `CLAUDE.md` for the **Night Shift Config** section if present. If absent, use defaults — see `_multi-runner.md`.

## Order

Run these in order. Each is a self-contained bundle prompt; fetch the file, read it, execute it, then move on.

1. **plans** — https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/plans.md
2. **docs** — https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/docs.md
3. **code-fixes** — https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/code-fixes.md
4. **audits** — https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/audits.md

## Allowlist (optional)

If the caller passes `allowed_tasks` (a list of task ids), propagate it to each inner bundle. Each inner bundle intersects its own task list against the allowlist and skips non-matching tasks. Absent `allowed_tasks` = all tasks allowed (the default for a one-shot manual run).

## Rules

- Plans goes first because it may add features the doc tasks should then cover.
- Docs goes second because it commits markdown changes regardless of test state.
- Code-fixes goes third because it must keep tests green between tasks.
- Audits goes last because each task creates its own PR independent of the others.
- If any single bundle exits silently (nothing to do), continue with the next.
- If code-fixes hits a verification failure mid-bundle, stop code-fixes but still run audits.
- Append one line per bundle to `docs/NIGHTSHIFT-HISTORY.md` at the end (create the file if missing) under a `## Runs` heading at the top of the runs list. Format:
  ```
  - YYYY-MM-DD plans      <ok|silent|failed>  <terse note>
  - YYYY-MM-DD docs       <ok|silent|failed>  <terse note>
  - YYYY-MM-DD code-fixes <ok|silent|failed>  <terse note>
  - YYYY-MM-DD audits     <ok|silent|failed>  <terse note>
  ```
- Commit and push the history file.
- Print a final summary table showing bundle / status / notes.
