# Multi-repo Bundle 1 — Plans & Docs

You are running the Night Shift **Plans & Docs** bundle across **all repositories** cloned into this session.

## Discover repos
List sibling directories from your starting working directory. For each candidate, run `git rev-parse --show-toplevel` to confirm it's a git repository. Build the list of valid repos before starting the loop.

## Per-repo loop
For each repo, in directory-name order:

1. `cd` into the repo. Capture the current branch.
2. `git status --porcelain` — if the tree is dirty, log `dirty-skip` and continue with the next repo. **Do not** clean up someone else's in-progress work.
3. Check opt-out signals: skip with `opted-out` if `.nightshift-skip` exists at the repo root, or any of `CLAUDE.md` / `AGENTS.md` / `README.md` contains the line `Night Shift: skip`. Otherwise proceed — `CLAUDE.md` is optional, defaults apply when missing (see `_multi-runner.md`).
4. Fetch and execute the per-repo bundle:
   **https://raw.githubusercontent.com/perandre/night-shift/v3/bundles/1-plans-docs.md**
   The bundle's own rules apply (skip excluded tasks, continue on silent exits, push per CLAUDE.md push protocol).
5. If the inner bundle throws an unrecoverable error, catch it. Record `failed` for this repo and a one-line reason. **Do not abort the multi-repo run.**
6. `cd` back to the parent directory before starting the next repo.

## Final report
After processing all repos, print a single summary table and stop. No prose after the table.

```
Night Shift bundle 1 (Plans & Docs) — multi-repo summary

| Repo | Status | Notes |
|------|--------|-------|
| ...  | ok / skipped / dirty-skip / opted-out / failed | <terse> |
```
