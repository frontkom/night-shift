# Multi-repo runner — shared protocol

This file documents the loop semantics used by the `multi-*.md` wrappers. It is not fetched by triggers directly — it's reference reading for the wrappers and for humans editing them.

## How the trigger lays out repos

When a trigger declares multiple `sources[]` entries with `git_repository`, the remote environment clones each one as a sibling directory at the top of the working tree:

```
<working dir>/
├── repo-a/        ← .git inside
├── repo-b/
├── repo-c/
└── night-shift/   ← this repo, always cloned, used for the runs log
```

Discover dynamically — do not hardcode paths:

```bash
ls -1 -d */ 2>/dev/null
( cd "$dir" && git rev-parse --show-toplevel 2>/dev/null )
```

A directory is a repo if `git rev-parse --show-toplevel` succeeds. Always exclude the `night-shift` repo from the per-bundle loop — it's the runner's own home, not a target.

## The loop — one isolated subagent per repo

**Critical:** each target repo must be processed in its own subagent (via the `Task` tool) so the main wrapper's context window does not accumulate state across repos. The main wrapper only stores a single one-line result per repo.

For each discovered target repo, in directory-name order:

1. From the main wrapper, briefly `cd` into the repo to:
   - Run `git status --porcelain` — if dirty, record `dirty-skip` and continue.
   - Check opt-out signals. Record `opted-out` and continue if **any** of these are true:
     - A file `.nightshift-skip` exists at the repo root.
     - `CLAUDE.md`, `AGENTS.md`, or `README.md` contains a line `Night Shift: skip`.
   - Capture the absolute repo path. `cd` back to the parent directory.
2. Otherwise, dispatch a `Task` subagent with a self-contained prompt that:
   - Tells the subagent its working directory (the absolute repo path).
   - Gives it the URL of the inner bundle to fetch and execute.
   - Instructs it to perform all of the inner bundle's work.
   - Instructs it to **append one line to `docs/NIGHTSHIFT-HISTORY.md`** at the end of its run, then commit + push that file alongside its other changes (or as a standalone commit if nothing else changed). The line format is documented below.
   - Asks it to return **one single line** to the wrapper, format: `<status> | <terse note>` where status ∈ {`ok`, `failed`}.
3. Capture only that one-line result. Do **not** read or echo the subagent's intermediate work.
4. Move on to the next repo.

If a subagent dispatch itself throws an unrecoverable error, record `failed | dispatch error: <reason>` and continue. Never abort the multi-repo run.

## Per-repo history file: `docs/NIGHTSHIFT-HISTORY.md`

Each subagent appends one line per bundle run to `docs/NIGHTSHIFT-HISTORY.md` in the target repo (creating the file if it doesn't exist). This is the visible artifact in the project repo itself — anyone with repo access can see what Night Shift has been doing.

Format (newest at the top, under the `## Runs` heading):

```markdown
# Night Shift history

This file is maintained automatically by Night Shift. Each line records one
bundle run. See https://github.com/perandre/night-shift for what each bundle does.

## Runs

- 2026-04-08 plans      ok      PR #142 — build-planned-features phase 2
- 2026-04-07 docs       ok      changelog updated; 2 ADRs added
- 2026-04-07 code-fixes silent  no coverage gaps found
```

Columns: `<YYYY-MM-DD> <bundle id> <status> <terse note>`. Status values: `ok`, `silent` (everything self-skipped), `failed`.

## Run log in the night-shift repo: `runs/YYYY-MM.md`

The `night-shift` repo is always cloned alongside target repos. After all subagents finish and the summary table is built, the main wrapper appends the entire summary table to `runs/YYYY-MM.md` in that repo (creating the file if it doesn't exist), then commits and pushes. This gives the night-shift maintainer a single-place historical log across all projects, even projects they don't have direct access to.

Format: append a level-2 heading per run:

```markdown
## 2026-04-08 21:00 UTC — plans (3 repos)

| Repo | Status | Notes |
|------|--------|-------|
| ... | ... | ... |
```

If pushing the night-shift repo fails (e.g. credentials missing), log it but **do not** fail the bundle run — the per-repo history files in target repos are the user-facing artifact and are independent.

## Defaults when no config exists

If a target repo has no `CLAUDE.md` (or one without a `## Night Shift Config` section), fall back to:

| Setting | Default |
|---|---|
| Test command | First of: `npm test`, `pnpm test`, `yarn test`, `bun test`, `cargo test`, `pytest`, `go test ./...`. If none, test-needing tasks self-skip. |
| Build command | First of: `npm run build`, `pnpm build`, `yarn build`, `bun run build`, `cargo build`, `go build ./...`. If none, build-needing tasks self-skip. |
| Push protocol | `git push origin <branch>` |
| Default branch | Read from `git symbolic-ref refs/remotes/origin/HEAD` |
| Doc language | Match existing docs in `docs/` or `README.md`; fall back to English |
| Key pages | Heuristic: top-level routes in the framework's pages/app directory |
| Task subset | All tasks; each one self-skips when not applicable |

A project with explicit Night Shift Config in `CLAUDE.md` always overrides these defaults.

## Final report

After all repos are processed, print one table:

```
Night Shift <bundle-name> — multi-repo summary

| Repo         | Status   | Notes                              |
|--------------|----------|------------------------------------|
| frisk-survey | ok       | 2 commits pushed                   |
| snippy       | opted-out| .nightshift-skip present           |
| phone-home   | failed   | test command exited 1 in add-tests |
```

Status values: `ok`, `silent`, `opted-out`, `dirty-skip`, `failed`. Keep notes terse. No further prose after the table — but the wrapper still has work to do (append to `runs/YYYY-MM.md` in night-shift repo) before finishing.
