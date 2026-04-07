# Multi-repo Bundle 2 — Code Self-Verified

You are running the Night Shift **Code self-verified** bundle across **all repositories** cloned into this session.

## Discover repos
List sibling directories from your starting working directory. For each candidate, run `git rev-parse --show-toplevel` to confirm it's a git repository. Build the list of valid repos before starting the loop.

## Per-repo loop
For each repo, in directory-name order:

1. `cd` into the repo.
2. `git status --porcelain` — if the tree is dirty, log `dirty-skip` and continue with the next repo.
3. Check opt-out signals: skip with `opted-out` if `.nightshift-skip` exists at the repo root, or any of `CLAUDE.md` / `AGENTS.md` / `README.md` contains the line `Night Shift: skip`. Otherwise proceed — `CLAUDE.md` is optional, defaults apply when missing (see `_multi-runner.md`).
4. Fetch and execute the per-repo bundle:
   **https://raw.githubusercontent.com/perandre/night-shift/v3/bundles/2-code-verified.md**
   That bundle runs tasks 05 → 06 → 07 strictly in order and stops the per-repo run on a failed test or build. That stop is **per repo only**.
5. Catch any unrecoverable error. Record `failed` for this repo and a one-line reason. Continue with the next repo.
6. `cd` back to the parent directory before starting the next repo.

## Final report
After processing all repos, print a single summary table and stop. No prose after the table.

```
Night Shift bundle 2 (Code Self-Verified) — multi-repo summary

| Repo | Status | Notes |
|------|--------|-------|
| ...  | ok / skipped / dirty-skip / opted-out / failed | <terse> |
```
