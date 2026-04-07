# Multi-repo: Plans

You are running the Night Shift **Plans** bundle across **all target repositories** cloned into this session.

## Discover repos
List sibling directories at the top of your working tree. For each candidate, confirm it is a git repository via `git rev-parse --show-toplevel`. **Exclude the `night-shift` repo itself** — it is the runner's home, not a target.

## Per-repo loop — isolated subagent per repo

For each discovered target repo, in directory-name order:

1. From the main wrapper, briefly `cd` into the repo to:
   - Run `git status --porcelain` — if dirty, record `dirty-skip` and continue.
   - Check opt-out signals. Record `opted-out` and continue if any of: `.nightshift-skip` exists at the repo root, or `CLAUDE.md` / `AGENTS.md` / `README.md` contains the line `Night Shift: skip`.
   - Capture the absolute repo path. `cd` back to the parent.
2. Dispatch a `Task` subagent with this prompt (substitute `{REPO_PATH}`):

   ```
   Your working directory is {REPO_PATH}. cd into it now.

   Fetch https://raw.githubusercontent.com/perandre/night-shift/v7/bundles/plans.md
   and execute it against this repository. The bundle picks one pending plan phase
   and opens a PR for it. At most one PR per repo per night.

   CLAUDE.md is optional. Honor `## Night Shift Config` if present, otherwise apply
   the defaults from
   https://raw.githubusercontent.com/perandre/night-shift/v7/bundles/_multi-runner.md.

   At the end of your run, append ONE LINE to docs/NIGHTSHIFT-HISTORY.md (create the
   file if missing) under the `## Runs` heading at the top of the runs list. Format:
       - YYYY-MM-DD plans      <ok|silent|failed>  <terse note, max 80 chars>
   Then commit + push the history file (alongside other commits or as its own commit).

   Return EXACTLY ONE LINE to me in this format:
       <ok|silent|failed> | PR: <url or —> | <terse note, max 60 chars>
   ```
3. Capture only the one-line result. Do not echo subagent work into your own context.
4. Move on to the next repo.

If a subagent dispatch itself fails, record `failed | PR: — | dispatch error: <reason>`.

## Final report
Print this summary table:

```
Night Shift plans — multi-repo summary

| Repo | Status | PR | Notes |
|------|--------|----|-------|
| ...  | ok / silent / opted-out / dirty-skip / failed | <url or —> | <terse> |
```

## Append run log to night-shift repo
After the summary table is printed, write an entry to `runs/YYYY-MM.md` inside the cloned `night-shift` repo (create the file if missing). Use UTC date. Format:

```markdown
## YYYY-MM-DD HH:MM UTC — plans (<N> repos)

<the same summary table from above>
```

Then commit and push the night-shift repo:

```bash
cd <path-to-night-shift-clone>
git add runs/
git commit -m "log: plans run YYYY-MM-DD"
git push origin main
```

If the push fails (no credentials, no write access), log it but do **not** fail the run. The per-repo `docs/NIGHTSHIFT-HISTORY.md` files in the target repos are the user-facing artifact and are independent.
