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

**Per-repo execution order — dispatch the small items first.** Within each repo, the order is fixed and load-bearing:

1. **Per-repo prelude** (Step 1 below — dirty/opt-out/labels/CLAUDE.md parse).
2. **`work-on-issues` fan-out** if allowlisted (see "work-on-issues dispatch" section). One subagent per discovered tagged issue.
3. **`work-on-jira-issues` fan-out** if allowlisted (see "work-on-jira-issues dispatch" section). One subagent per discovered tagged Jira issue.
4. **Plan-file fan-out** (Step 2 below — one subagent per surviving plan file by default; plans marked `night-shift: parallel-phases` further fan out to one subagent per pending phase).
5. **PR body sweep** (after every dispatch above completes for this repo).

This order matters: the plan fan-out can dispatch 10+ subagents and burn most of the wrapper's budget. If issues + jira ran *after* plans (the historical order), a budget-exhausted wrapper would silently never reach them — causing the symptom of "tagged issues sitting open for nights with no PR and no skip-comment." Issues and Jira typically discover a small number of items per repo, so running them first costs a small, predictable amount of context and guarantees they fire.

**No PR cap.** The wrapper does not throttle the number of PRs opened per morning. Throughput is the explicit goal; review is bounded by the per-issue / per-phase scoping (each subagent owns one narrow unit of work), not by a count ceiling.

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
   - Each **surviving** plan file becomes its own work-item `{repo, app_path, scoped_config, plan_file, phase_index}`. **Every** surviving plan must be dispatched — no plan-count cap. If a repo has 20 pending plans, the wrapper dispatches 20 subagents (each in its own context window, so the cost scales linearly without contention).
   - **Parallel-phase fan-out (opt-in).** For each surviving plan file, look for a `night-shift: parallel-phases` marker in the file's frontmatter, an HTML comment, or a top-of-file metadata block. When present, the plan author is asserting that its pending phases are mutually independent — each can branch off the default branch and land its own PR without depending on any other pending phase's changes. In that case, expand the plan into one work-item *per pending phase*: each carries the same `{repo, app_path, scoped_config, plan_file}` plus an explicit `phase_index` (1-based, in plan order). When the marker is absent (the default), emit one work-item with `phase_index = —` and the subagent handles phases sequentially as today.
   - The `parallel-phases` opt-in is a quality contract: phases that share schema migrations, depend on each other's exports, or sequentially mutate the same file are **not** independent and the marker must be omitted. There is no automatic independence detection — the plan author makes the call.
   - If an app-scope has zero plan files at all (after discovery), emit one work-item with `plan_file = —` so it can report `silent` in the summary. If there were plan files but the pre-filter rejected all of them, do **not** emit an empty work-item — the per-plan `not-applicable` rows already cover that case.
   - Capture the absolute repo path. `cd` back to the parent.
2. For each work-item from this repo, dispatch a `Task` subagent with this prompt (substitute `{REPO_PATH}`, `{APP_PATH}` — literal `—` when repo-wide, `{SCOPED_CONFIG}` as inline JSON / YAML, `{PLAN_FILE}` — literal `—` when no plans, `{PHASE_INDEX}` — literal `—` for sequential plans, integer for `parallel-phases` plans):

   ```
   Your working directory is {REPO_PATH}. cd into it now.
   App scope: {APP_PATH}          # "—" means repo-wide, single-app mode
   Plan file: {PLAN_FILE}         # "—" means no plans to process; exit silent
   Phase index: {PHASE_INDEX}     # "—" means sequential mode (implement multiple phases);
                                  # integer means parallel-phases mode (implement THIS phase only)
   Allowed tasks: [build-planned-features]   # this subagent runs this one task only
   Scoped config: {SCOPED_CONFIG}  # resolved test/build/plans dir/key pages

   If PLAN_FILE is "—", return `silent | PR: — | no plan files` and stop.

   Otherwise, fetch
   https://raw.githubusercontent.com/frontkom/night-shift/main/tasks/build-planned-features.md
   and execute it against THIS ONE PLAN FILE ONLY. Do not scan for other plans; the
   dispatcher has already fanned out one subagent per plan (and, when the plan is
   marked `night-shift: parallel-phases`, one subagent per pending phase).

   - If PHASE_INDEX is "—": implement as many pending phases of PLAN_FILE as
     reasonably fit in one PR, bundled. See the task file's "How far to go in
     one run" heading for stop conditions.
   - If PHASE_INDEX is an integer: implement ONLY that phase (1-based, in plan
     order). Branch off the default branch — not off any other phase's branch.
     Open one PR titled `phase {PHASE_INDEX}`. Do not touch other phases'
     scope. If your phase's tests fail, leave a Night Shift Notes entry under
     that phase and open a `[blocked]` PR — do not bleed into adjacent phases.

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

## work-on-issues dispatch (scope: repo, one subagent per tagged issue)

**Dispatched BEFORE the plan-file fan-out** for this repo (see "Per-repo execution order" above). After Step 1's prelude completes, check if `work-on-issues` is in the repo's allowlist. If so, **discover tagged issues at the wrapper level** (cheap — no subagent yet) and fan out one subagent per issue:

```bash
( cd "$REPO_PATH" && \
  gh issue list --label "night-shift" --state open --json number,title --jq 'sort_by(.number) | .[] | .number' )
```

Print one discovery line listing the numbers found: `Discovered tagged issues: #12, #15, #18 (3 total).` If the list is empty, print `Discovered tagged issues: none.` and skip to the Jira dispatch. There is **no count cap** — every tagged issue gets its own subagent.

For each discovered issue, dispatch one `Task` subagent (substitute `{REPO_PATH}` and `{ISSUE_NUMBER}`):

```
Your working directory is {REPO_PATH}. cd into it now.

Issue: #{ISSUE_NUMBER}    # exactly one issue — do not scan for others

Fetch https://raw.githubusercontent.com/frontkom/night-shift/main/tasks/work-on-issues.md
and execute it against THIS ONE ISSUE ONLY. The dispatcher has already fanned out
one subagent per tagged issue; do not run the discovery query and do not process
any other issues. Open at most one PR.

CLAUDE.md is optional. Honor `## Night Shift Config` if present, otherwise apply
the defaults from
https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/_multi-runner.md.

Return EXACTLY ONE LINE to me in this format:
    <ok|silent|failed> | PR: <url or —> | #{ISSUE_NUMBER} — <terse note, max 60 chars>
```

Record one summary row per issue with `App = —`, `Plan = work-on-issues #<n>`. The wrapper-level PR body sweep covers any PRs these subagents opened.

## work-on-jira-issues dispatch (scope: repo, one subagent per tagged Jira issue)

**Dispatched BEFORE the plan-file fan-out** for this repo, immediately after the `work-on-issues` fan-out (or after skipping it when not allowlisted). Check if `work-on-jira-issues` is in the repo's allowlist. If so, **discover tagged Jira issues at the wrapper level** by calling the Atlassian Rovo MCP `Search with JQL` tool. The wrapper has the connector attached; the subagents don't need it for their narrowed prompts. Use the JQL from CLAUDE.md (`Jira project key:` is required, `Jira label:` defaults to `night-shift`):

```
project = <KEY> AND labels = "<LABEL>" AND statusCategory != Done ORDER BY created ASC
```

If `CLAUDE.md` lacks `Jira project key:`, skip the entire Jira dispatch silently. If the Rovo connector is not attached at the wrapper level, skip silently. If the JQL search returns zero issues, print `Discovered tagged Jira issues: none.` and continue.

Otherwise, print one discovery line: `Discovered tagged Jira issues: FGPW-12, FGPW-15 (2 total).` There is **no count cap** — every tagged Jira issue gets its own subagent.

For each discovered Jira key, dispatch one `Task` subagent (substitute `{REPO_PATH}` and `{ISSUE_KEY}`):

```
Your working directory is {REPO_PATH}. cd into it now.

Jira issue: {ISSUE_KEY}    # exactly one issue — do not scan for others

Fetch https://raw.githubusercontent.com/frontkom/night-shift/main/tasks/work-on-jira-issues.md
and execute it against THIS ONE JIRA ISSUE ONLY. The dispatcher has already
fanned out one subagent per tagged Jira issue; do not run the JQL search and
do not process any other issues. Open at most one PR.

The task uses the Atlassian Rovo MCP connector. If the connector is not
attached to this subagent, return `failed | PR: — | rovo connector not
available` — the wrapper will pick this up.

CLAUDE.md is optional. Honor `## Night Shift Config` if present, otherwise apply
the defaults from
https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/_multi-runner.md.

Return EXACTLY ONE LINE to me in this format:
    <ok|silent|failed> | PR: <url or —> | {ISSUE_KEY} — <terse note, max 60 chars>
```

Record one summary row per Jira key with `App = —`, `Plan = work-on-jira-issues <KEY>`. The wrapper-level PR body sweep covers any PRs these subagents opened.

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
