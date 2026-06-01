# Multi-repo: Plans

You are running the Night Shift **Plans** bundle across **all target repositories** cloned into this session.

**Before doing anything else**, print a single status line so the user sees immediate output:

```
Night Shift plans bundle starting (multi-repo)...
```

## Parse the per-repo allowlist first

Before discovering repos, scan **your own invocation prompt** for a `<night-shift-config>…</night-shift-config>` block and parse the `repos:` map out of it. See `bundles/_multi-runner.md` → **Per-repo task allowlist** for the exact contract, parsing rules, and fallback behavior. Summary:

- If the block is absent or malformed, treat as "no allowlist supplied" and log `allowlist: none (running all tasks)` in the final summary.
- Otherwise, for each repo key, the value is a list of task ids from `manifest.yml` that are allowed for that repo. Unknown ids → warn and ignore. A repo absent from the map → all tasks allowed.

For the **plans** bundle, the relevant task ids are `build-planned-features`, `work-on-issues`, and `work-on-jira-issues`. A repo whose allowlist does not include **any** of these must be recorded as `not-selected` and dispatched to no subagents.

## Discover repos
List sibling directories at the top of your working tree. For each candidate, confirm it is a git repository via `git rev-parse --show-toplevel`.

## Dispatcher-subagent architecture

The plans bundle has the highest fan-out of any bundle: one subagent per plan file, one per tagged GitHub issue, one per tagged Jira issue. A busy repo can easily produce 100+ work-items. Dispatching that many `Task` calls **directly from this wrapper** would blow out the wrapper's own context window — each Task adds ~250 tokens (prompt template + one-line return) to the wrapper's running history, and even at the cheap end 100 dispatches = ~25K tokens of pure orchestration overhead. The wrapper would then truncate / stop before finishing dispatch, and the items it never reached would silently produce no PR and no audit-trail comment. (This is exactly the failure mode that left 21 of 22 high-severity frontkom/frisk issues with no NS interaction in the 2026-05-31 run.)

**Fix: a dispatcher-subagent layer.** Per repo, this wrapper makes at most **three** `Task` calls — one per category (plans, issues, jira). Each call spawns a dedicated **dispatcher subagent** in its own fresh ~200K context window. That dispatcher does the discovery, the fan-out (one grandchild `Task` per work-item), and the result collection. The wrapper sees only one combined result per category, not one per work-item.

```
                  wrapper (this prompt)
                  /          |          \
        plans-dispatcher  issues-dispatcher  jira-dispatcher    ← one Task per category
            / | \                / | \              / | \
       plan plan plan       issue issue issue     key key key   ← one Task per work-item
```

Each dispatcher has a fresh, near-empty context, so it can fan out 100+ grandchildren without running into the same dispatch-budget exhaustion the wrapper would hit. Discovery happens **inside** the dispatcher (in its own context), not in the wrapper — the wrapper just passes the repo path + scoped config.

**Per-repo dispatch order.** Within each repo, dispatch the three category dispatchers **sequentially in this order**:

1. **Per-repo prelude** (Step 1 below — dirty/opt-out/labels/CLAUDE.md parse).
2. **`plans-dispatcher`** subagent (if `build-planned-features` is allowlisted for this repo).
3. **`issues-dispatcher`** subagent (if `work-on-issues` is allowlisted for this repo).
4. **`jira-dispatcher`** subagent (if `work-on-jira-issues` is allowlisted for this repo).
5. **Label sweep** then **PR body sweep**.

Plans go first because they are the largest, slowest, and highest-value work-items. If anything degrades during the run, plans should have the best chance of having completed. Issues and Jira are smaller per-item and can land later in the night.

**No PR cap.** The wrapper does not throttle the number of PRs opened per morning. Throughput is the explicit goal; review is bounded by the per-issue / per-phase scoping (each work-item owns one narrow unit of work), not by a count ceiling. The 90-second PR-creation throttle (see `_multi-runner.md`) still applies across all subagents in the routine.

## Per-repo loop

For each discovered target repo, in directory-name order:

### 1. Per-repo prelude

From the main wrapper, briefly `cd` into the repo to:

- Look up the repo in the parsed allowlist. Compute the **per-repo allowlist set**:
  - `plans_allowed`   = `build-planned-features` is allowed
  - `issues_allowed`  = `work-on-issues` is allowed
  - `jira_allowed`    = `work-on-jira-issues` is allowed
  - If none are allowed, record one summary row `not-selected` and continue to the next repo (no dispatch).
- Run `git status --porcelain` — if dirty, record `dirty-skip` and continue.
- Check opt-out signals. Record `opted-out` and continue if any of: `.nightshift-skip` exists at the repo root, or `CLAUDE.md` / `AGENTS.md` / `README.md` contains the line `Night Shift: skip`.
- **Ensure the `night-shift` label exists on the repo** (idempotent — silent if it already exists). Run this once per repo before dispatching subagents:
  ```
  gh label create night-shift --color "0e8a16" --description "Automated by Night Shift" 2>/dev/null || true
  ```
  See `bundles/_multi-runner.md` → "Labels (created at wrapper level, applied at task level)".
- Capture the absolute repo path. Capture `## Night Shift Config` from `CLAUDE.md` verbatim (as one block of text — the dispatcher subagents re-parse it). If the file is missing or has no Night Shift Config section, pass the literal string `—`.
- Capture the per-repo Jira config from the parsed allowlist block: `jira_project_key` and `jira_label`. Either may be `—`.
- `cd` back to the parent.

### 2. Dispatch the plans-dispatcher subagent (if `plans_allowed`)

Make one `Task` call with the prompt below (substitute `{REPO_PATH}`, `{CLAUDE_MD_NS_CONFIG}`):

```
You are the Night Shift PLANS DISPATCHER for one repo. Your job is to discover every plan file in this repo, fan out one Task subagent per plan file (or per pending phase for plans marked `night-shift: parallel-phases`), collect one-line results, and return them all to your caller in a single response.

Repo: {REPO_PATH}    # cd into this directory now and stay there for the whole run.

Night Shift Config (from CLAUDE.md, verbatim — parse `apps:` block if present):
---
{CLAUDE_MD_NS_CONFIG}
---

Allowed task: build-planned-features

### Step A — build app scopes
Parse the Night Shift Config above. If it contains an `apps:` block, build one app-scope per `apps[]` entry (each with its own `app_path` + merged `scoped_config`). Otherwise build a single app-scope with `app_path = —`.

### Step B — discover plan files (filenames only; do NOT read bodies)
For each app-scope, list plan files under `PLANS_DIR` (which is `<app_path>/<plans dir>` when scoped, else `<plans dir>` from config, default `docs`). Recognise all four naming conventions in a single pass:
- `*-PLAN.md` (suffix, e.g. `MONOREPO-TEST-PLAN.md`)
- `PLAN-*.md` (prefix, e.g. `PLAN-JOURNAL.md`)
- `*.plan.md` (dotted, e.g. `migration.plan.md`)
- Any markdown file inside a `plans/` subdirectory of `PLANS_DIR` (e.g. `docs/plans/foo.md`)

Concretely:
```
find "$PLANS_DIR" -maxdepth 1 -type f \( -name '*-PLAN.md' -o -name 'PLAN-*.md' -o -name '*.plan.md' \)
find "$PLANS_DIR/plans" -maxdepth 2 -type f -name '*.md' 2>/dev/null
```
De-duplicate the union. **A new plan file appearing in the repo must show up here on the very next run** — no manual registration step. If a plan with one of these names is silently ignored, that is a discovery bug.

**Do NOT read plan bodies.** Your context is the place we are saving from bloat — the per-plan grandchildren read their own plans in their own contexts. The done-vs-pending judgment is delegated to each plan's grandchild, which can also inspect repo/migration state.

Print one discovery line up front: `Discovered plans: A, B, C (N total)` per app-scope.

### Step C — parallel-phases opt-in
Run one filename-only grep over the discovered plans:
```
grep -l 'night-shift: parallel-phases' <discovered plan files> 2>/dev/null
```
For each plan the grep returns (opt-in, rare), and only those, read that one file to enumerate its pending phases. Expand it into one work-item per pending phase — each carries the same `{repo, app_path, scoped_config, plan_file}` plus an explicit `phase_index` (1-based, in plan order). Every plan the grep does NOT return (the default) emits a single work-item with `phase_index = —`. Reading the handful of opt-in plans is bounded; reading all of them is the bug this design removes.

The `parallel-phases` opt-in is a quality contract: phases that share schema migrations, depend on each other's exports, or sequentially mutate the same file are NOT independent and the marker must be omitted. There is no automatic independence detection.

### Step D — fan out one Task per work-item
If an app-scope has zero plan files, emit one work-item with `plan_file = —` so it can report `silent` in your return.

For each work-item, dispatch a Task subagent with this prompt (substitute fields):

```
Your working directory is {REPO_PATH}. cd into it now.
App scope: {APP_PATH}          # "—" means repo-wide, single-app mode
Plan file: {PLAN_FILE}         # "—" means no plans to process; exit silent
Phase index: {PHASE_INDEX}     # "—" means sequential mode (implement multiple phases);
                               # integer means parallel-phases mode (implement THIS phase only)
Allowed tasks: [build-planned-features]
Scoped config: {SCOPED_CONFIG}  # resolved test/build/plans dir/key pages

If PLAN_FILE is "—", return `silent | PR: — | no plan files` and stop.

Otherwise, fetch
https://raw.githubusercontent.com/frontkom/night-shift/main/tasks/build-planned-features.md
and execute it against THIS ONE PLAN FILE ONLY. Do not scan for other plans; the
dispatcher has already fanned out one subagent per plan (and per pending phase
for `parallel-phases` plans).

First read the plan (the dispatcher did NOT pre-read it). If it is already fully
implemented, or marked blocked / deferred / on hold / archived, or empty / has
no parseable pending unit, do NOT open a PR — return
`silent | PR: — | not-applicable: <reason>` and stop. Check actual repo state,
not just the prose: a phase whose tables / migrations / exports already exist is
implemented even if the plan still says "pending", and a "Blocked on X" note is
stale (so the plan IS actionable) if X now exists on the default branch.

- If PHASE_INDEX is "—": implement as many pending phases of PLAN_FILE as
  reasonably fit in one PR, bundled. Multi-file refactors are in scope — see
  the task file. No artificial file/line caps.
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

Issue these Task calls **in parallel** where possible — a single message with multiple Task tool uses runs them concurrently, and that's exactly what we want here. The concurrency cap is whatever the harness imposes; just fire them all and let it queue.

### Step E — return to your caller
Print and return the following block (and nothing else — no narration, no summary table; the wrapper will assemble that from your block):

```
PLANS-DISPATCHER {REPO_PATH}
Discovered plans: <plan-name>, <plan-name>, ... (N total per app-scope, repeated if multiple apps)
- <ok|silent|failed> | <app_path or —> | PR: <url or —> | <plan-slug> — <terse>
- <ok|silent|failed> | <app_path or —> | PR: <url or —> | <plan-slug> — <terse>
...
END
```

One line per work-item, in the order you dispatched them. If a Task dispatch itself errored, record `failed | <app_path> | PR: — | dispatch error: <reason>`. **Never stop early** — every plan must get a dispatch attempt, even if earlier plans failed.
```

### 3. Dispatch the issues-dispatcher subagent (if `issues_allowed`)

Make one `Task` call with the prompt below (substitute `{REPO_PATH}`):

```
You are the Night Shift ISSUES DISPATCHER for one repo. Your job is to discover every GitHub Issue labeled `night-shift` in this repo, fan out one Task subagent per issue, collect one-line results, and return them all to your caller in a single response.

Repo: {REPO_PATH}    # cd into this directory now and stay there for the whole run.

Allowed task: work-on-issues

### Step A — discover tagged issues
Run:
```
gh issue list --label "night-shift" --state open --json number,title --jq 'sort_by(.number) | .[] | .number'
```

Print one discovery line up front: `Discovered tagged issues: #N1, #N2, ... (N total)`. If the list is empty, print `Discovered tagged issues: none.`, return the END block immediately with no work-items, and stop.

There is **no count cap** — every tagged issue gets its own subagent. A repo with 117 open issues spawns 117 grandchildren. That is the whole point of the dispatcher-subagent design: your fresh context has the room to do this; the wrapper's didn't.

### Step B — fan out one Task per issue
For each discovered issue, dispatch a Task subagent (substitute `{ISSUE_NUMBER}`):

```
Your working directory is {REPO_PATH}. cd into it now.

Issue: #{ISSUE_NUMBER}    # exactly one issue — do not scan for others

Fetch https://raw.githubusercontent.com/frontkom/night-shift/main/tasks/work-on-issues.md
and execute it against THIS ONE ISSUE ONLY. The dispatcher has already fanned out
one subagent per tagged issue; do not run the discovery query and do not process
any other issues. Open at most one PR.

Multi-file refactors and architectural changes are in scope — that's the whole
point of Night Shift. No file-count caps. The only legitimate skips are missing
human decisions, missing external access, and genuinely vague specs (see the
task file's "Evaluate scope" section). Leave a comment naming the specific
blocker when you skip — never skip silently.

CLAUDE.md is optional. Honor `## Night Shift Config` if present, otherwise apply
the defaults from
https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/_multi-runner.md.

Return EXACTLY ONE LINE to me in this format:
    <ok|silent|failed> | PR: <url or —> | #{ISSUE_NUMBER} — <terse note, max 60 chars>
```

Issue Task calls in parallel where possible (single message with multiple tool uses). The harness queues anything past its concurrency cap.

### Step C — return to your caller
Print and return:

```
ISSUES-DISPATCHER {REPO_PATH}
Discovered tagged issues: #N1, #N2, ... (N total)
- <ok|silent|failed> | PR: <url or —> | #N — <terse>
- <ok|silent|failed> | PR: <url or —> | #N — <terse>
...
END
```

One line per issue, in the order you dispatched them. If a Task dispatch itself errored, record `failed | PR: — | #N — dispatch error: <reason>`. **Never stop early** — every issue must get a dispatch attempt.
```

### 4. Dispatch the jira-dispatcher subagent (if `jira_allowed`)

Make one `Task` call with the prompt below (substitute `{REPO_PATH}`, `{JIRA_PROJECT_KEY}`, `{JIRA_LABEL}`, `{CLAUDE_MD_NS_CONFIG}`):

```
You are the Night Shift JIRA-ISSUES DISPATCHER for one repo. Your job is to discover every Jira issue labeled `{JIRA_LABEL}` in project `{JIRA_PROJECT_KEY}`, fan out one Task subagent per Jira key, collect one-line results, and return them all to your caller in a single response.

Repo: {REPO_PATH}    # cd into this directory now and stay there for the whole run.

Jira project key: {JIRA_PROJECT_KEY}   # may be "—" (resolved below if so)
Jira label: {JIRA_LABEL}               # defaults to "night-shift"

Night Shift Config (from CLAUDE.md, verbatim — fallback source for the Jira key):
---
{CLAUDE_MD_NS_CONFIG}
---

Allowed task: work-on-jira-issues

### Step A — resolve the Jira project key
If `{JIRA_PROJECT_KEY}` is "—", read the CLAUDE.md config above for a `Jira project key:` line. If still no key, print `Discovered tagged Jira issues: skipped (no project key)`, return the END block with no work-items, and stop. (This is fine — not every repo is mirrored to Jira.)

### Step B — discover tagged Jira issues via Rovo MCP
Use the Atlassian Rovo MCP connector that this routine has attached. Call **Search with JQL** with:

```
project = <KEY> AND labels = "<LABEL>" AND statusCategory != Done ORDER BY created ASC
```

If the Rovo connector is not callable in this session (connector not attached, OAuth lapsed, etc.), print `Discovered tagged Jira issues: skipped (rovo not available)`, return the END block with no work-items, and stop.

Print one discovery line up front: `Discovered tagged Jira issues: KEY-12, KEY-15, ... (N total)`. If the JQL returns zero issues, print `Discovered tagged Jira issues: none.`, return the END block with no work-items, and stop.

There is **no count cap** — every tagged Jira issue gets its own subagent.

### Step C — fan out one Task per Jira key
For each discovered key, dispatch a Task subagent (substitute `{ISSUE_KEY}`):

```
Your working directory is {REPO_PATH}. cd into it now.

Jira issue: {ISSUE_KEY}    # exactly one issue — do not scan for others

Fetch https://raw.githubusercontent.com/frontkom/night-shift/main/tasks/work-on-jira-issues.md
and execute it against THIS ONE JIRA ISSUE ONLY. The dispatcher has already
fanned out one subagent per tagged Jira issue; do not run the JQL search and
do not process any other issues. Open at most one PR.

The task uses the Atlassian Rovo MCP connector. If the connector is not
attached to this subagent, return `failed | PR: — | rovo connector not
available` — the dispatcher will pick this up.

Multi-file refactors and architectural changes are in scope. No file-count
caps. The only legitimate skips are missing human decisions, missing external
access, and genuinely vague specs (see the task file's "Evaluate scope"
section). Leave a Jira comment naming the specific blocker when you skip —
never skip silently.

CLAUDE.md is optional. Honor `## Night Shift Config` if present, otherwise apply
the defaults from
https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/_multi-runner.md.

Return EXACTLY ONE LINE to me in this format:
    <ok|silent|failed> | PR: <url or —> | {ISSUE_KEY} — <terse note, max 60 chars>
```

Issue Task calls in parallel where possible.

### Step D — return to your caller
Print and return:

```
JIRA-DISPATCHER {REPO_PATH}
Discovered tagged Jira issues: KEY-N, KEY-M, ... (N total)
- <ok|silent|failed> | PR: <url or —> | KEY-N — <terse>
- <ok|silent|failed> | PR: <url or —> | KEY-M — <terse>
...
END
```

One line per Jira key, in the order you dispatched them. If a Task dispatch itself errored, record `failed | PR: — | KEY-N — dispatch error: <reason>`. **Never stop early** — every Jira key must get a dispatch attempt.
```

### 5. Label sweep + PR body sweep

After all three category dispatchers have returned for this repo, run the **label sweep** then the **PR body sweep**. The body sweep finds PRs by label, so the label sweep must run first — otherwise PRs whose grandchild dropped `--label night-shift` are invisible to the body sweep. Both are idempotent.

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

### 6. Parse dispatcher returns into summary rows

Each dispatcher returned a block in this shape:
```
{NAME}-DISPATCHER {REPO_PATH}
Discovered ...: ... (N total)
- ok | ...
- silent | ...
...
END
```

Walk the lines between the header and `END`, mapping each to a row in the final summary table:
- A line `- ok | <app_path or —> | PR: <url> | <slug> — <terse>` → `Status: ok` row
- A line `- silent | ... | not-applicable: <reason>` → `Status: not-applicable` row
- Other `silent | ...` → `Status: silent` row
- `failed | ... | dispatch error: ...` → `Status: failed` row
- A line of the form `Discovered ...` → an informational pre-table bullet (see "Final report")

The wrapper never reads plan / issue bodies and never makes a not-applicable call itself — that determination always happens inside a grandchild.

## Final report

Print this summary table and stop. The summary table is the primary artifact — it appears in the routines dashboard and is how the user reviews the run, alongside the PR list (`gh pr list --label night-shift`); filter by title prefix (`night-shift/plan:`, `night-shift/issue:`, `night-shift/jira:`) to narrow to this bundle.

```
Night Shift plans — multi-repo summary

| Repo | App | Plan/Issue/Jira | Status | PR | Notes |
|------|-----|-----------------|--------|----|-------|
| ...  | <app_path or —> | <plan-slug or #N or KEY-N or —> | ok / silent / not-applicable / not-selected / opted-out / dirty-skip / failed | <url or —> | <terse> |
```

One row per work-item (one per plan, one per issue, one per Jira key). `App` is `—` for repo-wide work-items (issues, jira, single-app repos). The `Plan/Issue/Jira` cell:
- `<plan-slug>` for plan rows
- `#<n>` for GitHub issue rows
- `<JIRA-KEY>` for Jira rows
- `—` when the category was empty / skipped

A repo excluded from the allowlist produces one row with `App = —`, `Plan/Issue/Jira = —`, `Status = not-selected`.

Include each dispatcher's `Discovered ...` line and any `allowlist: …` / `allowlist warning: …` lines from the parsing step as bullet points beneath the table so the user sees them on the routines dashboard.
