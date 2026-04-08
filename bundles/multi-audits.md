# Multi-repo: Audits

You are running the Night Shift **Audits** bundle across **all target repositories** cloned into this session.

## Discover repos
List sibling directories at the top of your working tree. For each candidate, confirm via `git rev-parse --show-toplevel`.

## Per-work-item loop — isolated subagent per (repo, app)

All four audit tasks are `scope: app` in `manifest.yml`, so monorepo fan-out applies. `find-security-issues` keeps a repo-wide secret-scan pre-step (see the task file); the per-app part is the code review. See `bundles/_multi-runner.md` for the full discovery rule.

For each discovered target repo, in directory-name order:

1. From the main wrapper, briefly `cd` into the repo to:
   - `git status --porcelain` — if dirty, record `dirty-skip` and continue.
   - Check opt-out signals (`.nightshift-skip`, or `Night Shift: skip` in `CLAUDE.md` / `AGENTS.md` / `README.md`). Record `opted-out` and continue if any are present.
   - Parse `## Night Shift Config` in `CLAUDE.md`. If it contains an `apps:` block, build one work-item per `apps[]` entry (with merged `scoped_config`). Otherwise build a single work-item with `app_path = —`.
   - Capture the absolute repo path. `cd` back to the parent.
2. For each work-item, in `app_path` order, dispatch a `Task` subagent with this prompt (substitute `{REPO_PATH}`, `{APP_PATH}`, `{SCOPED_CONFIG}`, `{RUN_REPO_SECRET_SCAN}` — `true` for the first work-item of a repo, `false` afterwards):

   ```
   Your working directory is {REPO_PATH}. cd into it now.
   App scope: {APP_PATH}          # "—" means repo-wide, single-app mode
   Scoped config: {SCOPED_CONFIG}
   Run repo-wide secret scan: {RUN_REPO_SECRET_SCAN}

   Fetch https://raw.githubusercontent.com/perandre/night-shift/main/bundles/audits.md
   and execute it against this repository, scoped to {APP_PATH} when it is not "—".
   The bundle runs find-security-issues, find-bugs, improve-seo, and improve-performance.
   Each task creates its own branch + PR. Return to the default branch with a clean
   working tree before each task.

   When APP_PATH is not "—":
   - Each task walks only files under APP_PATH. Key pages come from scoped config.
   - Branch names include the app slug:
         nightshift/<area>-<app-slug>-YYYY-MM-DD
   - PR titles name the app:
         nightshift/<area>: <app_path> — <short description>
   - Skip the secret scan step in find-security-issues unless RUN_REPO_SECRET_SCAN is true.

   CLAUDE.md is optional. Honor `## Night Shift Config` if present, otherwise apply
   the defaults from
   https://raw.githubusercontent.com/perandre/night-shift/main/bundles/_multi-runner.md.

   At the end of your run, append ONE LINE to docs/NIGHTSHIFT-HISTORY.md (create the
   file if missing) under the `## Runs` heading at the top of the runs list. Format:
       - YYYY-MM-DD audits     <app_path or —>  <ok|silent|failed>  <PR count>; <terse note, max 60 chars>
   Then commit + push the history file.

   Return EXACTLY ONE LINE to me in this format:
       <ok|silent|failed> | PRs: <comma-separated URLs or —> | <terse note, max 60 chars>
   ```
3. Capture only the one-line result. Do not echo subagent work into your own context.
4. Move on to the next work-item.

If a subagent dispatch itself fails, record `failed | PRs: — | dispatch error: <reason>`.

## Final report
Print this summary table and stop. The summary table is the primary artifact — it appears in the trigger dashboard. **Do not** write the summary to any external repo; the per-repo `docs/NIGHTSHIFT-HISTORY.md` files in each target repo are the only persisted history.

```
Night Shift audits — multi-repo summary

| Repo | App | Status | PRs opened | Notes |
|------|-----|--------|-----------|-------|
| ...  | <app_path or —> | ok / silent / opted-out / dirty-skip / failed | <urls or —> | <terse> |
```

The `App` column shows `—` for single-app repos and one row per app for monorepos that declare `apps:`.
