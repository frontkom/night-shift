# Multi-repo: Plans

You are running the Night Shift **Plans** bundle across **all target repositories** cloned into this session.

**Before doing anything else**, capture the wall-dashboard start time and print a single status line so the user sees immediate output:

```bash
NS_RUN_START_EPOCH=$(date +%s)
NS_RUN_START_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
NS_BUNDLE=plans
echo "Night Shift plans bundle starting (multi-repo)..."
```

Hold `NS_RUN_START_EPOCH`, `NS_RUN_START_TS`, `NS_BUNDLE`, and an `NS_PROCESSED=()` bash array (filled as you build the summary table) in shell state. They feed the wall-dashboard logging step at the very end. See `bundles/_multi-runner.md` → **Wall-dashboard logging** for the protocol.

## Parse the per-repo allowlist first

Before discovering repos, scan **your own invocation prompt** for a `<night-shift-config>…</night-shift-config>` block and parse the `repos:` map out of it. See `bundles/_multi-runner.md` → **Per-repo task allowlist** for the exact contract, parsing rules, and fallback behavior. Summary:

- If the block is absent or malformed, treat as "no allowlist supplied" and log `allowlist: none (running all tasks)` in the final summary.
- Otherwise, for each repo key, the value is a list of task ids from `manifest.yml` that are allowed for that repo. Unknown ids → warn and ignore. A repo absent from the map → all tasks allowed.

For the **plans** bundle, the relevant task ids are `build-planned-features` and `work-on-issues`. A repo whose allowlist does not include **either** of these must be recorded as `not-selected` and dispatched to no subagents. If only one of the two is allowed, run only that task's dispatch logic and skip the other.

## Discover repos
List sibling directories at the top of your working tree. For each candidate, confirm it is a git repository via `git rev-parse --show-toplevel`.

## Per-work-item loop — isolated subagent per (repo, app, plan)

`build-planned-features` is `scope: app` in `manifest.yml`, so a repo with an `apps:` block fans out to one work-item per app. **On top of that, plans fan out further: one subagent per plan file.** Every pending plan gets its own agent and its own PR — no plan is ever skipped because another plan ran first.

**Per-repo execution order — dispatch the small caps first.** Within each repo, the order is fixed and load-bearing:

1. **Per-repo prelude** (Step 1 below — dirty/opt-out/labels/CLAUDE.md parse).
2. **`work-on-issues` dispatch** if allowlisted (see "work-on-issues dispatch" section). Hard cap: 3 issues / one subagent.
3. **`work-on-jira-issues` dispatch** if allowlisted (see "work-on-jira-issues dispatch" section). Hard cap: 3 issues / one subagent.
4. **Plan-file fan-out** (Step 2 below — one subagent per surviving plan file; can be 10+ subagents).
5. **PR body sweep** (after every dispatch above completes for this repo).

This order matters: the plan fan-out can dispatch 10+ subagents and burn most of the wrapper's budget. If issues + jira ran *after* plans (the historical order), a budget-exhausted wrapper would silently never reach them — causing the symptom of "tagged issues sitting open for nights with no PR and no skip-comment." Issues and jira are bounded to ≤3 issues each, so running them first costs a small, predictable amount of context and guarantees they fire.

For each discovered target repo, in directory-name order:

1. From the main wrapper, briefly `cd` into the repo to:
   - Look up the repo in the parsed allowlist. If `build-planned-features` is **not** in the repo's allowed list, record `not-selected` and continue (no dispatch for this repo).
   - Run `git status --porcelain` — if dirty, record `dirty-skip` and continue.
   - Check opt-out signals. Record `opted-out` and continue if any of: `.nightshift-skip` exists at the repo root, or `CLAUDE.md` / `AGENTS.md` / `README.md` contains the line `Night Shift: skip`.
   - **Ensure the `night-shift` label exists on the repo** (idempotent — silent if it already exists). Run this once per repo before dispatching subagents:
     ```
     gh label create night-shift --color "0e8a16" --description "Automated by Night Shift" 2>/dev/null || true
     ```
     See `bundles/_multi-runner.md` → "Labels (created at wrapper level, applied at task level)".
   - Parse `## Night Shift Config` in `CLAUDE.md`. If it contains an `apps:` block, build one app-scope per `apps[]` entry (each with its own `app_path` + merged `scoped_config`). Otherwise build a single app-scope with `app_path = —`.
   - **For each app-scope, list plan files.** Resolve `PLANS_DIR`: `<app_path>/<plans dir>` when scoped, else `<plans dir>` (default `docs`). Plans can use any of these naming conventions — discover **all** of them in a single pass:
     - `*-PLAN.md` (suffix style, e.g. `MONOREPO-TEST-PLAN.md`)
     - `PLAN-*.md` (prefix style, e.g. `PLAN-JOURNAL.md`, `PLAN-BATCH-TRANSACTIONS.md`)
     - `*.plan.md` (dotted style, e.g. `migration.plan.md`)
     - Any markdown file inside a `plans/` subdirectory of `PLANS_DIR` (e.g. `docs/plans/foo.md`)

     Concretely:
     ```
     find "$PLANS_DIR" -maxdepth 1 -type f \( -name '*-PLAN.md' -o -name 'PLAN-*.md' -o -name '*.plan.md' \)
     find "$PLANS_DIR/plans" -maxdepth 2 -type f -name '*.md' 2>/dev/null
     ```
     De-duplicate the union. **A new plan file appearing in the repo must show up as a discovered plan on the very next run** — no manual registration step. If a plan with one of these names is silently ignored, that is a discovery bug, not a "the plan was deferred" outcome.
   - **Print the discovered plan list at the start of the run** (before dispatching any subagents) so the human can see what the wrapper found vs. what they expected. Format: one line listing every discovered plan name, comma-separated. Example: `Discovered plans: MONOREPO-TEST-PLAN, PLAN-JOURNAL, PLAN-BATCH-TRANSACTIONS, ... (13 total)`. This is the single best signal that discovery is working.
   - **Pre-filter plans before dispatching subagents.** For each discovered plan file, do a cheap read at the wrapper level (no subagent yet) and **skip** the plan if any of the following is true:
     - The plan's title or front matter marks it **Deferred**, **Blocked**, **On hold**, or **Archived**.
     - **Every** phase / item / step / milestone in the plan is already marked done. Look for any of: `**Status: Implemented`, `**Status: Done`, `[x]`, `~~…~~` strikethrough, `✅`, or a bold `Status:` line whose value is `Implemented`/`Done`/`Complete`. If you cannot find any pending unit, the plan is fully implemented.
     - The plan file is empty or has no parseable units.
   - Plans skipped by the pre-filter get **one** wrapper-level row in the summary table (`Status: not-applicable`) — they do **not** spin up a subagent. This keeps the silent rate low and avoids spending a subagent budget on plans known to have nothing to do.
   - Each **surviving** plan file becomes its own work-item `{repo, app_path, scoped_config, plan_file}`. **Every** surviving plan must be dispatched — no plan-count cap. If a repo has 20 pending plans, the wrapper dispatches 20 subagents (each in its own context window, so the cost scales linearly without contention).
   - If an app-scope has zero plan files at all (after discovery), emit one work-item with `plan_file = —` so it can report `silent` in the summary. If there were plan files but the pre-filter rejected all of them, do **not** emit an empty work-item — the per-plan `not-applicable` rows already cover that case.
   - Capture the absolute repo path. `cd` back to the parent.
2. For each work-item from this repo, dispatch a `Task` subagent with this prompt (substitute `{REPO_PATH}`, `{APP_PATH}` — literal `—` when repo-wide, `{SCOPED_CONFIG}` as inline JSON / YAML, `{PLAN_FILE}` — literal `—` when no plans):

   ```
   Your working directory is {REPO_PATH}. cd into it now.
   App scope: {APP_PATH}          # "—" means repo-wide, single-app mode
   Plan file: {PLAN_FILE}         # "—" means no plans to process; exit silent
   Allowed tasks: [build-planned-features]   # this subagent runs this one task only
   Scoped config: {SCOPED_CONFIG}  # resolved test/build/plans dir/key pages

   If PLAN_FILE is "—", return `silent | PR: — | no plan files` and stop.

   Otherwise, fetch
   https://raw.githubusercontent.com/frontkom/night-shift/main/tasks/build-planned-features.md
   and execute it against THIS ONE PLAN FILE ONLY. Do not scan for other plans; the
   dispatcher has already fanned out one subagent per plan. Implement as many
   pending phases of PLAN_FILE as reasonably fit in one PR and open one PR for
   the bundled result. See the task file's "How far to go in one run" heading
   for stop conditions.

   When APP_PATH is not "—":
   - Branch name must include the app slug:
         night-shift/plan-<app-slug>-<plan-slug>-YYYY-MM-DD
     where <app-slug> is the last segment of APP_PATH (e.g. "web" for "apps/web").
   - PR title must name the app and the phase range:
         night-shift/plan: <app_path> — <plan-name> <phase-range>
     where <phase-range> is e.g. "phase 2", "phases 2–4", or suffix
     "(completes plan)" when this PR lands the last pending phase.

   CLAUDE.md is optional. Honor `## Night Shift Config` if present, otherwise apply
   the defaults from
   https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/_multi-runner.md.

   Return EXACTLY ONE LINE to me in this format:
       <ok|silent|failed> | PR: <url or —> | <plan-slug> — <terse note, max 60 chars>
   ```
3. Capture only the one-line result. Do not echo subagent work into your own context.
4. Move on to the next work-item. **Never stop early** — every plan must get its own dispatch attempt, even if earlier plans failed.

If a subagent dispatch itself fails, record `failed | PR: — | dispatch error: <reason>` in the summary.

After all work-items for this repo (the `work-on-issues` and `work-on-jira-issues` dispatches that ran before the plan fan-out, plus every plan-file subagent) have completed, run the **label sweep** then the **PR body sweep** before moving to the next repo. The body sweep finds PRs by label, so the label sweep must run first — otherwise PRs whose subagent dropped `--label night-shift` are invisible to the body sweep. Both are idempotent.

**Label sweep** — adds `night-shift` to any open PR whose title matches `^night-shift/` (the per-task contract) **or** `^chore:.*[Nn]ight[- ]?[Ss]hift` (external bundle/digest PRs that consolidate Night Shift PRs) but is missing the label. `--limit 1000` defends against `gh pr list`'s 30-default silently dropping recently-opened PRs in busy repos:

```bash
( cd "$REPO_PATH" && \
  gh pr list --state open --limit 1000 --json number,title,labels --jq '
    .[] | select(.title | test("^night-shift/|^chore:.*[Nn]ight[- ]?[Ss]hift"; "i"))
        | select((.labels | map(.name)) | index("night-shift") | not)
        | .number' \
    | xargs -I{} -r gh pr edit {} --add-label night-shift )
```

**PR body sweep** — repairs bodies that contain literal `\n` sequences (subagent skipped the post-create body fix):

```bash
( cd "$REPO_PATH" && \
  for pr in $(gh pr list --label night-shift --state open --limit 1000 --json number --jq '.[].number'); do
    body=$(gh pr view "$pr" --json body -q .body)
    case "$body" in
      *'\n'*)
        printf '%s' "$body" | python3 -c "import sys;sys.stdout.write(sys.stdin.read().replace(chr(92)+chr(110),chr(10)))" > /tmp/night-shift-body-fix.md
        gh pr edit "$pr" --body-file /tmp/night-shift-body-fix.md
        ;;
    esac
  done )
```

Pre-filtered plans (skipped before dispatch — fully implemented, deferred, blocked, etc.) appear in the summary table as `Status: not-applicable` rows; no subagent is dispatched.

## work-on-issues dispatch (scope: repo, once per repo)

**Dispatched BEFORE the plan-file fan-out** for this repo (see "Per-repo execution order" above). After Step 1's prelude completes, check if `work-on-issues` is in the repo's allowlist. If so, dispatch **one `Task` subagent per repo** (not per app — `work-on-issues` is `scope: repo`):

```
Your working directory is {REPO_PATH}. cd into it now.

Fetch https://raw.githubusercontent.com/frontkom/night-shift/main/tasks/work-on-issues.md
and execute it against this repository. Process up to 3 open GitHub Issues
labeled "night-shift", opening one PR per issue.

CLAUDE.md is optional. Honor `## Night Shift Config` if present, otherwise apply
the defaults from
https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/_multi-runner.md.

Return EXACTLY ONE LINE to me in this format:
    <ok|silent|failed> | PRs: <comma-separated URLs or —> | <terse note, max 60 chars>
```

Record the result in the summary as a row with `App = —`, `Plan = work-on-issues`.

## work-on-jira-issues dispatch (scope: repo, once per repo)

**Dispatched BEFORE the plan-file fan-out** for this repo, immediately after the `work-on-issues` dispatch (or after skipping it when not allowlisted). Check if `work-on-jira-issues` is in the repo's allowlist. If so, dispatch **one `Task` subagent per repo**:

```
Your working directory is {REPO_PATH}. cd into it now.

Fetch https://raw.githubusercontent.com/frontkom/night-shift/main/tasks/work-on-jira-issues.md
and execute it against this repository. Process up to 3 open Jira issues
labelled "night-shift" from the project key configured in CLAUDE.md, opening
one GitHub PR per issue.

The task uses the Atlassian Rovo MCP connector — no API tokens or env vars
involved. It self-skips silently if any of the following is true:
- CLAUDE.md does not contain `Jira project key:` in `## Night Shift Config`.
- The Atlassian Rovo MCP connector is not attached to this routine.
- The JQL search returns zero issues.

CLAUDE.md is optional. Honor `## Night Shift Config` if present, otherwise apply
the defaults from
https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/_multi-runner.md.

Return EXACTLY ONE LINE to me in this format:
    <ok|silent|failed> | PRs: <comma-separated URLs or —> | <terse note, max 60 chars>
```

Record the result in the summary as a row with `App = —`, `Plan = work-on-jira-issues`. The wrapper-level PR body sweep already covers any PR opened by this dispatch (label-based, runs once per repo after all subagents finish), so no extra cleanup is needed here.

## Final report
Print this summary table and stop. The summary table is the primary artifact — it appears in the routines dashboard and is how the user reviews the run, alongside the PR list (`gh pr list --label night-shift`); filter by title prefix (`night-shift/plan:`, `night-shift/issue:`) to narrow to this bundle.

```
Night Shift plans — multi-repo summary

| Repo | App | Plan | Status | PR | Notes |
|------|-----|------|--------|----|-------|
| ...  | <app_path or —> | <plan-slug or —> | ok / silent / not-applicable / not-selected / opted-out / dirty-skip / failed | <url or —> | <terse> |
```

One row per (repo, app, plan). `App` is `—` for single-app repos. `Plan` is `—` when the app-scope had no plan files (the row will be `silent`). `Plan` is `work-on-issues` for the issues dispatch. A repo excluded from the allowlist produces one row with `App = —`, `Plan = —`, `Status = not-selected`.

Include any `allowlist: …` or `allowlist warning: …` lines from the parsing step as bullet points beneath the table so the user sees them on the routines dashboard.

## Wall-dashboard logging (last action)

After printing the summary table, append one JSONL event per processed repo to `dashboard/runs.jsonl` in the dashboard host repo. Follow the exact protocol in `bundles/_multi-runner.md` → **Wall-dashboard logging** → Step 2.

Recap of what to do here, no prose: use `NS_RUN_START_EPOCH`, `NS_BUNDLE=plans`, and the `NS_PROCESSED` array you've been filling. A repo is "processed" when its summary row's status is `ok`, `silent`, or `failed`. Best-effort — never let the dashboard append fail the routine.
