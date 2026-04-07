# Multi-repo Bundle 1 — Plans

You are running the Night Shift **Plans** bundle across **all repositories** cloned into this session.

## Discover repos
List sibling directories from your starting working directory. For each candidate, run `git rev-parse --show-toplevel` to confirm it is a git repository. Build the list of valid repos before starting the loop.

## Per-repo loop — isolated subagent per repo

**Context isolation requirement:** dispatch one `Task` subagent per repo. The main wrapper never executes bundle work itself.

For each discovered repo, in directory-name order:

1. From the main wrapper, briefly `cd` into the repo to:
   - Run `git status --porcelain` — if dirty, record `dirty-skip` and continue.
   - Check opt-out signals. Record `opted-out` and continue if any of: `.nightshift-skip` exists at the repo root, or `CLAUDE.md` / `AGENTS.md` / `README.md` contains the line `Night Shift: skip`.
   - Capture the absolute repo path. `cd` back to the parent.
2. Dispatch a `Task` subagent with this prompt (substitute `{REPO_PATH}`):

   ```
   Your working directory is {REPO_PATH}. cd into it now.

   Fetch https://raw.githubusercontent.com/perandre/night-shift/v6/bundles/1-plans.md
   and execute it against this repository. The bundle runs task 00 (implement plans),
   which picks one pending plan phase, implements it on a feature branch, and opens a PR.
   At most one PR per repo per night.

   CLAUDE.md is optional. Honor `## Night Shift Config` if present, otherwise apply the
   defaults from https://raw.githubusercontent.com/perandre/night-shift/v6/bundles/_multi-runner.md.

   When you are done, return EXACTLY ONE LINE in this format:
   <ok|failed> | PR: <url or —> | <terse note, max 60 chars>
   ```
3. Capture only the one-line result. Do not echo subagent work into your own context.
4. Move on to the next repo.

If a subagent dispatch itself fails, record `failed | PR: — | dispatch error: <reason>` and continue.

## Final report
After processing all repos, print a single summary table including PR URLs. No prose after the table.

```
Night Shift bundle 1 (Plans) — multi-repo summary

| Repo | Status | PR | Notes |
|------|--------|----|-------|
| ...  | ok / opted-out / dirty-skip / failed | <url or —> | <terse> |
```
