# Multi-repo runner — shared protocol

This file documents the loop semantics used by the `multi-*.md` wrappers. It is not fetched by triggers directly — it's reference reading for the wrappers and for humans editing them.

## How the trigger lays out repos

When a trigger declares multiple `sources[]` entries with `git_repository`, the remote environment clones each one as a sibling directory at the top of the working tree:

```
<working dir>/
├── repo-a/        ← .git inside
├── repo-b/
└── repo-c/
```

Discover dynamically — do not hardcode paths:

```bash
ls -1 -d */ 2>/dev/null
( cd "$dir" && git rev-parse --show-toplevel 2>/dev/null )
```

A directory is a repo if `git rev-parse --show-toplevel` succeeds.

## The loop — one isolated subagent per work-item

**Critical:** each work-item must be processed in its own subagent (via the `Task` tool) so the main wrapper's context window does not accumulate state across repos. The main wrapper only stores a single one-line result per work-item.

A **work-item** is either `{repo, app_path: null, scoped_config}` (single-app repo) or `{repo, app_path: "apps/<slug>", scoped_config}` (one per app in a monorepo). See **Discovery** below for how work-items are derived.

For each work-item, in deterministic order (repo directory name, then app path):

1. From the main wrapper, briefly `cd` into the repo to:
   - Run `git status --porcelain` — if dirty, record `dirty-skip` and continue (whole repo, not per-app).
   - Check opt-out signals. Record `opted-out` and continue if **any** of these are true:
     - A file `.nightshift-skip` exists at the repo root.
     - `CLAUDE.md`, `AGENTS.md`, or `README.md` contains a line `Night Shift: skip`.
   - Parse the **Night Shift Config** section in `CLAUDE.md` (optional). Build the list of work-items as described under **Discovery**.
   - Capture the absolute repo path. `cd` back to the parent directory.
2. For each work-item derived from this repo, dispatch a `Task` subagent with a self-contained prompt that:
   - Tells the subagent its working directory (the absolute repo path).
   - Tells it which app it is scoped to (`app_path`, or `—` for repo-wide).
   - Passes the **scoped config** (test command, build command, key pages, plans dir) resolved for this app.
   - Gives it the URL of the inner bundle to fetch and execute.
   - Instructs it to perform all of the inner bundle's work **inside `app_path`** for tasks marked `scope: app` in `manifest.yml`, and **repo-wide** for tasks marked `scope: repo`.
   - Instructs it to **append one line per (bundle, app) pair to `docs/NIGHTSHIFT-HISTORY.md`** at the end of its run, then commit + push that file alongside its other changes. The line format is documented below.
   - Asks it to return **one single line** to the wrapper, format: `<status> | <terse note>` where status ∈ {`ok`, `failed`}.
3. Capture only that one-line result. Do **not** read or echo the subagent's intermediate work.
4. Move on to the next work-item.

If a subagent dispatch itself throws an unrecoverable error, record `failed | dispatch error: <reason>` and continue. Never abort the multi-repo run.

## Discovery — expanding repos to work-items

After cloning a repo and passing the dirty / opt-out checks, build its work-item list:

1. Parse the **Night Shift Config** section in `CLAUDE.md` (if present).
2. If the config has no `apps:` block, or the config is absent entirely, emit **one work-item** with `app_path: null` and `scoped_config = top-level config` (or defaults — see below).
3. If the config has an `apps:` block:
   - For **each task in the bundle**, look up the task's `scope` in `manifest.yml`.
   - For tasks with `scope: app` (the default), emit **one work-item per `apps[]` entry**. Each work-item has `app_path = apps[i].path` and a `scoped_config` that merges the app entry over the top-level config (app entry wins on any overlap).
   - For tasks with `scope: repo`, emit **one work-item** for the whole repo with `app_path: null` and `scoped_config = top-level config` (ignoring `apps:`).
   - De-duplicate so the same (repo, app_path) work-item isn't dispatched twice within one bundle run.

**Config resolution rule (for `scope: app` tasks):**

```
resolved.test       = app.test       ?? top.test       ?? default
resolved.build      = app.build      ?? top.build      ?? default
resolved.key_pages  = app.key pages  ?? top.key pages  ?? heuristic(app_path)
resolved.plans_dir  = app.plans dir  ?? top.plans dir  ?? "<app_path>/docs"
```

For `scope: repo` tasks, always use the top-level config (never an `apps[i]` block), even in a monorepo.

## Summary table rows — per (repo, app)

When a repo declares `apps:`, the summary table prints **one row per (repo, app_path) work-item** for `scope: app` tasks, plus one row per repo for `scope: repo` tasks. Single-app repos (no `apps:` block) print exactly one row per repo, same as before.

## Per-repo history file: `docs/NIGHTSHIFT-HISTORY.md`

Each subagent appends one line per bundle run to `docs/NIGHTSHIFT-HISTORY.md` in the target repo (creating the file if it doesn't exist). This file lives in the target repo itself — anyone with access to that repo can see what Night Shift has been doing. Access control follows the repo's own permissions.

**Do not** write Night Shift logs to any other repo. In particular, do **not** write to the public `perandre/night-shift` repo — doing so would leak private project information (names, activity, commit counts) to a public location. Each target project is the authoritative log for its own Night Shift activity.

Format (newest at the top, under the `## Runs` heading):

```markdown
# Night Shift history

This file is maintained automatically by Night Shift. Each line records one
bundle run. See https://github.com/perandre/night-shift for what each bundle does.

## Runs

- 2026-04-08 plans      ok      PR #142 — build-planned-features phase 2
- 2026-04-07 docs       ok      changelog updated; 2 ADRs added
- 2026-04-07 code-fixes silent  no coverage gaps found
```

Columns: `<YYYY-MM-DD> <bundle id> <status> <terse note>`. Status values: `ok`, `silent` (everything self-skipped), `failed`.

**Monorepo variant.** When a repo declares `apps:`, `scope: app` task outcomes get an app column so it's obvious which team owns each row:

```markdown
- 2026-04-08 audits    apps/web    ok      PR #210 — perf sweep
- 2026-04-08 audits    apps/admin  silent  no low-risk perf wins
- 2026-04-08 docs      —           ok      1 ADR added (repo-wide)
```

Columns for monorepo rows: `<YYYY-MM-DD> <bundle id> <app_path or —> <status> <terse note>`. The `—` marker indicates a `scope: repo` task that ran once for the whole repo.

## Defaults when no config exists

If a target repo has no `CLAUDE.md` (or one without a `## Night Shift Config` section), fall back to:

| Setting | Default |
|---|---|
| Test command | First of: `npm test`, `pnpm test`, `yarn test`, `bun test`, `cargo test`, `pytest`, `go test ./...`. If none, test-needing tasks self-skip. |
| Build command | First of: `npm run build`, `pnpm build`, `yarn build`, `bun run build`, `cargo build`, `go build ./...`. If none, build-needing tasks self-skip. |
| Push protocol | `git push origin <branch>` |
| Default branch | Read from `git symbolic-ref refs/remotes/origin/HEAD` |
| Doc language | Match existing docs in `docs/` or `README.md`; fall back to English |
| Key pages | Heuristic: top-level routes in the framework's pages/app directory |
| Task subset | All tasks; each one self-skips when not applicable |

A project with explicit Night Shift Config in `CLAUDE.md` always overrides these defaults.

## Final report

After all repos are processed, print one table and stop. The summary table is the primary run artifact — it appears in the trigger dashboard output and is how the user reviews the run the next morning.

```
Night Shift <bundle-name> — multi-repo summary

| Repo         | App        | Status    | Notes                              |
|--------------|------------|-----------|------------------------------------|
| frisk-survey | —          | ok        | 2 commits pushed                   |
| turbo-site   | apps/web   | ok        | perf sweep PR opened               |
| turbo-site   | apps/admin | silent    | nothing to do                      |
| snippy       | —          | opted-out | .nightshift-skip present           |
| phone-home   | —          | failed    | test command exited 1 in add-tests |
```

The `App` column shows `—` for single-app repos and for `scope: repo` tasks. For monorepos with `apps:` configured, each `scope: app` task gets one row per app.

Status values: `ok`, `silent`, `opted-out`, `dirty-skip`, `failed`. Keep notes terse. No further prose after the table. Do not attempt to write the summary to any external location.
