# Multi-repo: Plans

You are running the Night Shift **Plans** bundle across **all target repositories** cloned into this session.

## Discover repos
List sibling directories at the top of your working tree. For each candidate, confirm it is a git repository via `git rev-parse --show-toplevel`.

## Per-work-item loop — isolated subagent per (repo, app)

`build-planned-features` is `scope: app` in `manifest.yml`, so a repo with an `apps:` block fans out to one subagent per app. Repos without `apps:` run once, as before. See `bundles/_multi-runner.md` for the full discovery rule.

For each discovered target repo, in directory-name order:

1. From the main wrapper, briefly `cd` into the repo to:
   - Run `git status --porcelain` — if dirty, record `dirty-skip` and continue.
   - Check opt-out signals. Record `opted-out` and continue if any of: `.nightshift-skip` exists at the repo root, or `CLAUDE.md` / `AGENTS.md` / `README.md` contains the line `Night Shift: skip`.
   - Parse `## Night Shift Config` in `CLAUDE.md`. If it contains an `apps:` block, build one work-item per `apps[]` entry (each with its own `app_path` + merged `scoped_config`). Otherwise build a single work-item with `app_path = —`.
   - Capture the absolute repo path. `cd` back to the parent.
2. For each work-item from this repo, dispatch a `Task` subagent with this prompt (substitute `{REPO_PATH}`, `{APP_PATH}` — use literal `—` when repo-wide, `{SCOPED_CONFIG}` as inline JSON / YAML):

   ```
   Your working directory is {REPO_PATH}. cd into it now.
   App scope: {APP_PATH}          # "—" means repo-wide, single-app mode
   Scoped config: {SCOPED_CONFIG}  # resolved test/build/plans dir/key pages

   Fetch https://raw.githubusercontent.com/perandre/night-shift/main/bundles/plans.md
   and execute it against this repository, scoped to {APP_PATH} when it is not "—".
   The bundle picks one pending plan phase and opens a PR for it. At most one PR per
   (repo, app) per night.

   When APP_PATH is not "—":
   - Read plans from <APP_PATH>/<plans dir from scoped config, default "docs">.
   - Branch name must include the app slug:
         nightshift/plan-<app-slug>-<plan-slug>-phase-<N>-YYYY-MM-DD
     where <app-slug> is the last segment of APP_PATH (e.g. "web" for "apps/web").
   - PR title must name the app:
         nightshift/plan: <app_path> — <plan-name> phase <N>

   CLAUDE.md is optional. Honor `## Night Shift Config` if present, otherwise apply
   the defaults from
   https://raw.githubusercontent.com/perandre/night-shift/main/bundles/_multi-runner.md.

   At the end of your run, append ONE LINE to docs/NIGHTSHIFT-HISTORY.md (create the
   file if missing) under the `## Runs` heading at the top of the runs list. Format:
       - YYYY-MM-DD plans      <app_path or —>  <ok|silent|failed>  <terse note, max 80 chars>
   Then commit + push the history file (alongside other commits or as its own commit).

   Return EXACTLY ONE LINE to me in this format:
       <ok|silent|failed> | PR: <url or —> | <terse note, max 60 chars>
   ```
3. Capture only the one-line result. Do not echo subagent work into your own context.
4. Move on to the next work-item.

If a subagent dispatch itself fails, record `failed | PR: — | dispatch error: <reason>`.

## Final report
Print this summary table and stop. The summary table is the primary artifact — it appears in the trigger dashboard and is how the user reviews the run. **Do not** write the summary to any external repo or location; the per-repo `docs/NIGHTSHIFT-HISTORY.md` files in each target repo are the only persisted history.

```
Night Shift plans — multi-repo summary

| Repo | App | Status | PR | Notes |
|------|-----|--------|----|-------|
| ...  | <app_path or —> | ok / silent / opted-out / dirty-skip / failed | <url or —> | <terse> |
```

The `App` column shows `—` for single-app repos and one row per app for monorepos that declare `apps:`.
