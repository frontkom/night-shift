# Multi-repo: Audits

You are running the Night Shift **Audits** bundle across **all target repositories** cloned into this session.

**Before doing anything else**, print a single status line so the user sees immediate output:
`Night Shift audits bundle starting (multi-repo)...`

## Parse the per-repo allowlist first

Before discovering repos, scan **your own invocation prompt** for a `<night-shift-config>…</night-shift-config>` block and parse the `repos:` map out of it. See `bundles/_multi-runner.md` → **Per-repo task allowlist** for the exact contract. If absent or malformed → no allowlist (all tasks allowed), log `allowlist: none (running all tasks)` in the summary.

Fetch `https://raw.githubusercontent.com/frontkom/night-shift/main/manifest.yml` once and collect the set of task ids where `bundle: audits` — this is the authoritative bundle task set. Do **not** hardcode a list here; new audit tasks added to the manifest must flow through automatically. For each repo compute `audits_allowed = allowlist[repo] ∩ <manifest audits tasks>`. If empty, record `not-selected` for that repo and dispatch nothing.

## Discover repos
List sibling directories at the top of your working tree. For each candidate, confirm via `git rev-parse --show-toplevel`.

## Per-work-item loop — isolated subagent per (repo, app)

All four audit tasks are `scope: app` in `manifest.yml`, so monorepo fan-out applies. `find-security-issues` keeps a repo-wide secret-scan pre-step (see the task file); the per-app part is the code review. See `bundles/_multi-runner.md` for the full discovery rule.

For each discovered target repo, in directory-name order:

1. From the main wrapper, briefly `cd` into the repo to:
   - Look up the repo in the parsed allowlist. If `audits_allowed` is empty, record `not-selected` and continue (no dispatch for this repo).
   - `git status --porcelain` — if dirty, record `dirty-skip` and continue.
   - Check opt-out signals (`.nightshift-skip`, or `Night Shift: skip` in `CLAUDE.md` / `AGENTS.md` / `README.md`). Record `opted-out` and continue if any are present.
   - Parse `## Night Shift Config` in `CLAUDE.md`. If it contains an `apps:` block, build one work-item per `apps[]` entry (with merged `scoped_config`). Otherwise build a single work-item with `app_path = —`.
   - Capture the absolute repo path. `cd` back to the parent.
2. For each work-item, in `app_path` order, dispatch a `Task` subagent with this prompt (substitute `{REPO_PATH}`, `{APP_PATH}`, `{SCOPED_CONFIG}`, `{RUN_REPO_SECRET_SCAN}` — `true` for the first work-item of a repo, `false` afterwards):

   ```
   Your working directory is {REPO_PATH}. cd into it now.
   App scope: {APP_PATH}          # "—" means repo-wide, single-app mode
   Scoped config: {SCOPED_CONFIG}
   Allowed tasks: {AUDITS_ALLOWED}   # YAML list of audit task ids for this repo
   Run repo-wide secret scan: {RUN_REPO_SECRET_SCAN}

   Fetch https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/audits.md
   and execute it against this repository, scoped to {APP_PATH} when it is not "—".
   Pass `allowed_tasks: AUDITS_ALLOWED` to the inner bundle so each audit task
   self-filters (tasks not in the list exit silently).
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
   https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/_multi-runner.md.

   **Do not** modify docs/NIGHTSHIFT-HISTORY.md from any feature branch — the wrapper
   appends the row on main after you return. See bundles/_multi-runner.md →
   "NIGHTSHIFT-HISTORY.md is wrapper-only".

   Return EXACTLY ONE LINE to me in this format:
       <ok|silent|failed> | PRs: <comma-separated URLs or —> | <terse note, max 60 chars>
   ```
3. Capture only the one-line result. Do not echo subagent work into your own context.
4. **On `main`** in `{REPO_PATH}`, append one line to `docs/NIGHTSHIFT-HISTORY.md` under the `## Runs` heading at the top of the runs list:
   ```
   - YYYY-MM-DD audits  <app_path or —>  <ok|silent|failed>  <PR count>; <terse note, max 60 chars>
   ```
   Commit (`docs: append nightshift history`) and push that single change. Do this for every dispatched subagent — including `silent` and `failed` ones — so every dispatched run leaves a row.
5. Move on to the next work-item.

If a subagent dispatch itself fails, record `failed | PRs: — | dispatch error: <reason>` and still append a `failed` history row on main.

## Final report
Print this summary table and stop. The summary table is the primary artifact — it appears in the routines dashboard. **Do not** write the summary to any external repo; the per-repo `docs/NIGHTSHIFT-HISTORY.md` files in each target repo are the only persisted history.

```
Night Shift audits — multi-repo summary

| Repo | App | Status | PRs opened | Notes |
|------|-----|--------|-----------|-------|
| ...  | <app_path or —> | ok / silent / not-selected / opted-out / dirty-skip / failed | <urls or —> | <terse> |
```

The `App` column shows `—` for single-app repos and one row per app for monorepos that declare `apps:`.
