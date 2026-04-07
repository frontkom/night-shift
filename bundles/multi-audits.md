# Multi-repo: Audits

You are running the Night Shift **Audits** bundle across **all target repositories** cloned into this session.

## Discover repos
List sibling directories at the top of your working tree. For each candidate, confirm via `git rev-parse --show-toplevel`. **Exclude the `night-shift` repo** — it is the runner's home, not a target.

## Per-repo loop — isolated subagent per repo

For each discovered target repo, in directory-name order:

1. From the main wrapper, briefly `cd` into the repo to:
   - `git status --porcelain` — if dirty, record `dirty-skip` and continue.
   - Check opt-out signals (`.nightshift-skip`, or `Night Shift: skip` in `CLAUDE.md` / `AGENTS.md` / `README.md`). Record `opted-out` and continue if any are present.
   - Capture the absolute repo path. `cd` back to the parent.
2. Dispatch a `Task` subagent with this prompt (substitute `{REPO_PATH}`):

   ```
   Your working directory is {REPO_PATH}. cd into it now.

   Fetch https://raw.githubusercontent.com/perandre/night-shift/v7/bundles/audits.md
   and execute it against this repository. The bundle runs find-security-issues, find-bugs,
   improve-seo, and improve-performance. Each task creates its own branch + PR. Return to
   the default branch with a clean working tree before each task.

   CLAUDE.md is optional. Honor `## Night Shift Config` if present, otherwise apply
   the defaults from
   https://raw.githubusercontent.com/perandre/night-shift/v7/bundles/_multi-runner.md.

   At the end of your run, append ONE LINE to docs/NIGHTSHIFT-HISTORY.md (create the
   file if missing) under the `## Runs` heading at the top of the runs list. Format:
       - YYYY-MM-DD audits     <ok|silent|failed>  <PR count>; <terse note, max 60 chars>
   Then commit + push the history file.

   Return EXACTLY ONE LINE to me in this format:
       <ok|silent|failed> | PRs: <comma-separated URLs or —> | <terse note, max 60 chars>
   ```
3. Capture only the one-line result. Do not echo subagent work into your own context.
4. Move on to the next repo.

If a subagent dispatch itself fails, record `failed | PRs: — | dispatch error: <reason>`.

## Final report
Print this summary table:

```
Night Shift audits — multi-repo summary

| Repo | Status | PRs opened | Notes |
|------|--------|-----------|-------|
| ...  | ok / silent / opted-out / dirty-skip / failed | <urls or —> | <terse> |
```

## Append run log to night-shift repo
After the summary table, append an entry to `runs/YYYY-MM.md` inside the cloned `night-shift` repo (create if missing). UTC date. Format:

```markdown
## YYYY-MM-DD HH:MM UTC — audits (<N> repos)

<the same summary table from above>
```

Then commit + push (`git add runs/ && git commit -m "log: audits run YYYY-MM-DD" && git push origin main`). If the push fails, log it but do **not** fail the bundle run.
