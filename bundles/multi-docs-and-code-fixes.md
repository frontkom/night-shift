# Multi-repo: Docs + Code fixes (composition)

You are running **two** Night Shift bundles in one session: **docs** first, then **code-fixes**, against all target repositories cloned into this session.

This is a runtime composition that exists because the trigger plan only allows 3 enabled triggers but Night Shift has 4 logical bundles. The two underlying bundles are unchanged — see `bundles/docs.md` and `bundles/code-fixes.md` for what each does.

## Why docs runs first

Docs tasks edit markdown only and never affect the test suite. Code-fixes tasks require a green test baseline. Running docs first means: even if a code-fixes task fails verification on a particular repo, that repo still gets its docs updates.

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

   You are running TWO night-shift bundles in sequence: docs, then code-fixes.

   Step 1 — DOCS:
   Fetch https://raw.githubusercontent.com/perandre/night-shift/v8/bundles/docs.md
   and execute it against this repository. Capture its outcome (ok / silent / failed)
   as the docs result.

   Step 2 — CODE FIXES (always run, regardless of docs outcome):
   Fetch https://raw.githubusercontent.com/perandre/night-shift/v8/bundles/code-fixes.md
   and execute it against this repository. Capture its outcome as the code-fixes result.

   CLAUDE.md is optional. Honor `## Night Shift Config` if present, otherwise apply
   the defaults from
   https://raw.githubusercontent.com/perandre/night-shift/v8/bundles/_multi-runner.md.

   At the end of your run, append TWO LINES to docs/NIGHTSHIFT-HISTORY.md (create the
   file if missing) under the `## Runs` heading at the top of the runs list:
       - YYYY-MM-DD docs       <ok|silent|failed>  <terse note, max 80 chars>
       - YYYY-MM-DD code-fixes <ok|silent|failed>  <terse note, max 80 chars>
   Then commit + push the history file.

   Return EXACTLY ONE LINE to me in this format (combined status):
       <status> | docs: <ok|silent|failed> | code-fixes: <ok|silent|failed> | <terse note>

   Where the combined status is:
   - `ok`     — at least one of docs / code-fixes did real work successfully
   - `silent` — both docs and code-fixes self-skipped with nothing to do
   - `failed` — at least one returned failed (the other may still have run successfully)
   ```
3. Capture only the one-line result. Do not echo subagent work into your own context.
4. Move on to the next repo.

If a subagent dispatch itself fails, record `failed | docs: — | code-fixes: — | dispatch error: <reason>`.

## Final report
Print this summary table:

```
Night Shift docs+code-fixes — multi-repo summary

| Repo | Status | Docs | Code fixes | Notes |
|------|--------|------|------------|-------|
| ...  | ok / silent / opted-out / dirty-skip / failed | ok / silent / failed / — | ok / silent / failed / — | <terse> |
```

## Append run log to night-shift repo
After the summary table, append an entry to `runs/YYYY-MM.md` inside the cloned `night-shift` repo (create if missing). UTC date. Format:

```markdown
## YYYY-MM-DD HH:MM UTC — docs+code-fixes (<N> repos)

<the same summary table from above>
```

Then commit + push (`git add runs/ && git commit -m "log: docs+code-fixes run YYYY-MM-DD" && git push origin main`). If the push fails, log it but do **not** fail the bundle run.
