# Multi-repo Bundle 3 — Code Self-Verified

You are running the Night Shift **Code self-verified** bundle across **all repositories** cloned into this session.

## Discover repos
List sibling directories from your starting working directory. For each candidate, run `git rev-parse --show-toplevel` to confirm it's a git repository. Build the list of valid repos before starting the loop.

## Per-repo loop — isolated subagent per repo

**Context isolation requirement:** dispatch one `Task` subagent per repo. The main wrapper never executes bundle work itself and never echoes the subagent's intermediate output into its own context.

For each discovered repo, in directory-name order:

1. From the main wrapper, briefly `cd` into the repo to:
   - Run `git status --porcelain` — if dirty, record `dirty-skip` and continue.
   - Check opt-out signals. Record `opted-out` and continue if any of: `.nightshift-skip` exists at the repo root, or `CLAUDE.md` / `AGENTS.md` / `README.md` contains the line `Night Shift: skip`.
   - Capture the absolute repo path. `cd` back to the parent.
2. Dispatch a `Task` subagent with this prompt (substitute `{REPO_PATH}`):

   ```
   Your working directory is {REPO_PATH}. cd into it now.

   Fetch https://raw.githubusercontent.com/perandre/night-shift/v6/bundles/3-code-verified.md
   and execute it against this repository. The bundle runs tasks 05 → 06 → 07 strictly in
   order and stops on a failed test or build.

   CLAUDE.md is optional. Honor `## Night Shift Config` if present, otherwise apply the
   defaults from https://raw.githubusercontent.com/perandre/night-shift/v6/bundles/_multi-runner.md.

   When you are done, return EXACTLY ONE LINE in this format:
   <ok|failed> | <terse note, max 80 chars>
   ```
3. Capture only the one-line result. Do not echo subagent work into your own context.
4. Move on to the next repo.

If a subagent dispatch itself fails, record `failed | dispatch error: <reason>` and continue.

## Final report
After processing all repos, print a single summary table and stop. No prose after the table.

```
Night Shift bundle 3 (Code Self-Verified) — multi-repo summary

| Repo | Status | Notes |
|------|--------|-------|
| ...  | ok / skipped / dirty-skip / opted-out / failed | <terse> |
```
