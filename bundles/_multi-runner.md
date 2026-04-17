# Multi-repo runner — shared protocol

This file documents the loop semantics used by the `multi-*.md` wrappers. It is not fetched by routines directly — it's reference reading for the wrappers and for humans editing them.

## Per-repo task allowlist (the `<night-shift-config>` block)

The skill stores the per-repo task selection **inside the routine prompt itself**, as a YAML block between explicit delimiters. The wrapper parses this block out of its own invocation prompt on every run and uses it to filter which tasks it dispatches per repo.

**Format** (exact delimiters, no variations):

```
<night-shift-config>
repos:
  https://github.com/owner/repo-a: [build-planned-features, update-changelog, add-tests]
  https://github.com/owner/repo-b: [find-bugs, improve-seo]
</night-shift-config>
```

- Keys are full `https://github.com/owner/repo` URLs (no `.git`, matching how they appear in the routine's `sources[]`). For a monorepo with `apps:`, a future version may accept `https://github.com/owner/repo#app-slug` keys; unknown `#…` suffixes must fall back to the bare repo key.
- Values are YAML lists of **task ids** from `manifest.yml` (e.g. `build-planned-features`, not `task 1`). Task ids are the contract end-to-end — never numbers.
- An empty list `[]` means "no tasks for this repo in this bundle"; the wrapper records `not-selected` in the summary and dispatches nothing for that repo.
- A repo absent from `repos:` defaults to **all tasks allowed** (same as no config block at all). This keeps single-repo ad-hoc invocations working.

**Parsing rules** — the wrapper is itself an LLM subagent, so robustness matters:

1. Scan your own invocation prompt for the literal strings `<night-shift-config>` and `</night-shift-config>`. Extract everything between.
2. Parse as YAML. If parsing fails, the delimiter is missing, or the block is empty → treat as "no allowlist supplied". Log **one line** in the final summary: `allowlist: none (running all tasks)`.
3. If a listed task id doesn't appear in `manifest.yml`, warn (one line in the summary: `allowlist warning: unknown task id <id> for <repo>`) and ignore that id. Never crash the run.
4. If a repo URL in `repos:` isn't among the cloned sources, warn (`allowlist warning: repo <url> in config but not cloned`) and ignore.

**How the wrapper applies the allowlist** — in the work-item loop, for each repo:

- Look up the repo's allowlist. Absent → all tasks allowed (this bundle's full task set from `manifest.yml`).
- Intersect the allowlist against the set of this bundle's tasks. If the intersection is empty, record `not-selected` for that repo and do not dispatch any subagents for it.
- Pass `allowed_tasks: [<intersection as YAML list>]` to every subagent dispatched for this repo. Subagents forward it to the inner bundle and each task, which self-check their own id against the list and exit silently if not present.

**When the user hand-edits the prompt.** The skill's add/remove/update-repo flows must **read the current routine prompt, parse the YAML, merge the change, and rewrite** — never regenerate from scratch. This preserves any hand-edits the user made in the routines dashboard.

## How the routine lays out repos

When a routine declares multiple `sources[]` entries with `git_repository`, the remote environment clones each one as a sibling directory at the top of the working tree:

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
   - Instructs it to **never modify `docs/NIGHTSHIFT-HISTORY.md`** — the wrapper appends history rows on `main` after the subagent returns. See **NIGHTSHIFT-HISTORY.md is wrapper-only** above.
   - Asks it to return **one single line** to the wrapper, format: `<status> | PR: <url or —> | <terse note>` where status ∈ {`ok`, `silent`, `failed`}.
3. Capture only that one-line result. Do **not** read or echo the subagent's intermediate work.
4. **On `main`, in the parent repo directory**, append one history row per (bundle, app) pair to `docs/NIGHTSHIFT-HISTORY.md` (creating the file if missing), then commit + push that single change. The line format is documented below. This append step is the wrapper's responsibility — it must happen after every subagent dispatch, including `silent` and `failed` outcomes.
5. Move on to the next work-item.

If a subagent dispatch itself throws an unrecoverable error, record `failed | dispatch error: <reason>` and continue. Never abort the multi-repo run.

## PR body formatting

**Critical:** When creating PRs with `gh pr create`, always use a HEREDOC for `--body` to preserve real newlines. **Never** pass the body as a single-line string with literal `\n` — GitHub renders those as visible `\n` characters instead of line breaks.

Correct:
```
gh pr create --title "..." --body "$(cat <<'EOF'
## Summary
- first change
- second change

---
_Run by Night Shift • <bundle>/<task>_
EOF
)"
```

Wrong — **do not do this**:
```
gh pr create --title "..." --body "Summary\n- first\n- second"
```

Each task file contains a HEREDOC template for its PR body. Follow the template structure exactly.

## Standardized PR title, labels, and footer (every task)

Every PR opened by Night Shift must follow these conventions so reviewers can filter, attribute, and audit the work consistently across all tasks and bundles.

### PR title format
Always `nightshift/<area>: <description>`. Slash + colon. The `<area>` is the task's short slug (`bug`, `a11y`, `tests`, `plan`, `docs`, `changelog`, `digest`, `suggestions`, `adr`, `seo`, `perf`, `security`, `i18n`, `issue`). Never use the parens form `nightshift(<area>):` for PR titles — the parens form is reserved for `git commit -m` messages on direct-to-main work, not for PR titles. When the task is scoped to an app, the title includes `<app_path> — ` after the colon.

### Labels (auto-created if missing)
Every `gh pr create` call must add two labels:
- `nightshift` — every Night Shift PR.
- `nightshift:<bundle>` — one of `nightshift:plans`, `nightshift:docs`, `nightshift:code-fixes`, `nightshift:audits`.

Before calling `gh pr create`, ensure both labels exist (idempotent — silent if they already exist):
```
gh label create nightshift --color "0e8a16" --description "Automated by Night Shift" 2>/dev/null || true
gh label create "nightshift:<bundle>" --color "1d76db" --description "Night Shift <bundle> bundle" 2>/dev/null || true
```

Then pass them to `gh pr create`:
```
gh pr create --title "nightshift/<area>: ..." \
  --label nightshift --label "nightshift:<bundle>" \
  --body "..."
```

### Body footer (last lines of every PR body)
Every PR body must end with this footer block, separated from the body by a horizontal rule:

```
---
_Run by Night Shift • <bundle>/<task-id>_
```

The footer is the only place the bundle + task id appears in the PR — keep it minimal. Tasks that have a Claude Code session URL available (passed by the dispatching wrapper) may add it as a second italic line:

```
---
_Run by Night Shift • <bundle>/<task-id>_  
_[Session log](<session-url>)_
```

The footer is required; the session line is optional. Together they make every PR self-describing for reviewers and auditable from `gh pr list --label nightshift`.

## NIGHTSHIFT-HISTORY.md is wrapper-only

Tasks **must not** modify `docs/NIGHTSHIFT-HISTORY.md` themselves. The history row is appended by the multi-runner wrapper on `main` (in a separate commit, never on a feature branch) **after** the dispatched subagent returns its one-line result. This keeps feature PRs free of housekeeping diffs and means the row contains the real PR number returned by the subagent.

Subagents return `<status> | PR: <url or —> | <terse note>` and the wrapper translates that into one history line on `main`. Do not append from the task; do not commit history changes on the feature branch.

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

After each subagent returns, the **wrapper** appends one line per bundle run to `docs/NIGHTSHIFT-HISTORY.md` in the target repo, on `main`, as a separate commit (creating the file if it doesn't exist). Subagents never touch this file — see **NIGHTSHIFT-HISTORY.md is wrapper-only** above for the rationale. This file lives in the target repo itself — anyone with access to that repo can see what Night Shift has been doing. Access control follows the repo's own permissions.

**Do not** write Night Shift logs to any other repo. In particular, do **not** write to the public `frontkom/night-shift` repo — doing so would leak private project information (names, activity, commit counts) to a public location. Each target project is the authoritative log for its own Night Shift activity.

Format (newest at the top, under the `## Runs` heading):

```markdown
# Night Shift history

This file is maintained automatically by Night Shift. Each line records one
bundle run. See https://github.com/frontkom/night-shift for what each bundle does.

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

After all repos are processed, print one table and stop. The summary table is the primary run artifact — it appears in the routines dashboard output and is how the user reviews the run the next morning.

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
