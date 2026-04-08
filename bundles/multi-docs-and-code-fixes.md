# Multi-repo: Docs + Code fixes (composition)

You are running **two** Night Shift bundles in one session: **docs** first, then **code-fixes**, against all target repositories cloned into this session.

This is a runtime composition that exists because the trigger plan only allows 3 enabled triggers but Night Shift has 4 logical bundles. The two underlying bundles are unchanged — see `bundles/docs.md` and `bundles/code-fixes.md` for what each does.

## Why docs runs first

Docs tasks edit markdown only and never affect the test suite. Code-fixes tasks require a green test baseline. Running docs first means: even if a code-fixes task fails verification on a particular repo, that repo still gets its docs updates.

## Discover repos
List sibling directories at the top of your working tree. For each candidate, confirm via `git rev-parse --show-toplevel`.

## Per-work-item loop — isolated subagent per (repo, app)

The **docs** bundle contains a mix of `scope: repo` tasks (`document-decisions`, `suggest-improvements`) and `scope: app` tasks (`update-changelog`, `update-user-guide`). The **code-fixes** bundle is entirely `scope: app`. See `bundles/_multi-runner.md` for the full discovery rule.

In a repo with an `apps:` block: one subagent is dispatched per `apps[]` entry. Inside that subagent, `scope: repo` tasks still only run during the **first** (lexicographically first app_path) dispatch — subsequent dispatches skip them to avoid duplicate ADRs / suggestions. Single-app repos (no `apps:` block) dispatch once with `app_path = —` and run every task.

For each discovered target repo, in directory-name order:

1. From the main wrapper, briefly `cd` into the repo to:
   - `git status --porcelain` — if dirty, record `dirty-skip` and continue.
   - Check opt-out signals (`.nightshift-skip`, or `Night Shift: skip` in `CLAUDE.md` / `AGENTS.md` / `README.md`). Record `opted-out` and continue if any are present.
   - Parse `## Night Shift Config` in `CLAUDE.md`. If it contains an `apps:` block, build one work-item per `apps[]` entry (with merged `scoped_config`). Otherwise build a single work-item with `app_path = —`.
   - Capture the absolute repo path. `cd` back to the parent.
2. For each work-item, in `app_path` order (lexicographic), dispatch a `Task` subagent with this prompt (substitute `{REPO_PATH}`, `{APP_PATH}`, `{RUN_REPO_SCOPED_TASKS}` — `true` only for the first work-item of this repo, `false` otherwise; always `true` when `app_path = —`):

   ```
   Your working directory is {REPO_PATH}. cd into it now.
   App scope: {APP_PATH}          # "—" means repo-wide, single-app mode
   Scoped config: {SCOPED_CONFIG}
   Run scope:repo tasks: {RUN_REPO_SCOPED_TASKS}  # when false, skip document-decisions + suggest-improvements

   You are running TWO night-shift bundles in sequence: docs, then code-fixes.

   Step 1 — DOCS:
   Fetch https://raw.githubusercontent.com/perandre/night-shift/main/bundles/docs.md
   and execute it against this repository, scoped to {APP_PATH} when it is not "—".
   When RUN_REPO_SCOPED_TASKS is false, skip the `document-decisions` and
   `suggest-improvements` tasks — they already ran in another app's subagent for
   this repo. Capture the outcome (ok / silent / failed) as the docs result.

   Step 2 — CODE FIXES (always run, regardless of docs outcome):
   Fetch https://raw.githubusercontent.com/perandre/night-shift/main/bundles/code-fixes.md
   and execute it against this repository, scoped to {APP_PATH} when it is not "—".
   All code-fixes tasks are scope: app. Capture the outcome as the code-fixes result.

   CLAUDE.md is optional. Honor `## Night Shift Config` if present, otherwise apply
   the defaults from
   https://raw.githubusercontent.com/perandre/night-shift/main/bundles/_multi-runner.md.

   At the end of your run, append TWO LINES to docs/NIGHTSHIFT-HISTORY.md (create the
   file if missing) under the `## Runs` heading at the top of the runs list:
       - YYYY-MM-DD docs       <app_path or —>  <ok|silent|failed>  <terse note>
       - YYYY-MM-DD code-fixes <app_path or —>  <ok|silent|failed>  <terse note>
   Then commit + push the history file.

   Return EXACTLY ONE LINE to me in this format (combined status):
       <status> | docs: <ok|silent|failed> | code-fixes: <ok|silent|failed> | <terse note>

   Where the combined status is:
   - `ok`     — at least one of docs / code-fixes did real work successfully
   - `silent` — both docs and code-fixes self-skipped with nothing to do
   - `failed` — at least one returned failed (the other may still have run successfully)
   ```
3. Capture only the one-line result. Do not echo subagent work into your own context.
4. Move on to the next work-item.

If a subagent dispatch itself fails, record `failed | docs: — | code-fixes: — | dispatch error: <reason>`.

## Final report
Print this summary table and stop. The summary table is the primary artifact — it appears in the trigger dashboard. **Do not** write the summary to any external repo; the per-repo `docs/NIGHTSHIFT-HISTORY.md` files in each target repo are the only persisted history.

```
Night Shift docs+code-fixes — multi-repo summary

| Repo | App | Status | Docs | Code fixes | Notes |
|------|-----|--------|------|------------|-------|
| ...  | <app_path or —> | ok / silent / opted-out / dirty-skip / failed | ok / silent / failed / — | ok / silent / failed / — | <terse> |
```

The `App` column shows `—` for single-app repos and one row per app for monorepos that declare `apps:`.
