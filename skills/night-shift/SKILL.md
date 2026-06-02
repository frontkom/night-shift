---
name: night-shift
description: |
  Set up, run, or manage Night Shift — a framework that schedules nightly maintenance jobs across multiple repositories. Runs via Claude Code routines and opens plans implementation, doc updates + code fixes, and audit PRs across the user's chosen repos.

  Use this skill when the user explicitly asks to: install Night Shift, set up Night Shift, schedule Night Shift, run a Night Shift bundle, add a repo to Night Shift, remove a repo from Night Shift, pause Night Shift on a project, or check Night Shift status.

  MANDATORY TRIGGERS: night-shift, night shift, nightshift, /night-shift, set up night shift, install night shift, schedule night shift, run night shift, night shift setup, night shift install
version: 2026-06-02b
---

# Night Shift

<!-- NIGHT_SHIFT_VERSION: 2026-06-02b -->

## Version check (run this first, every invocation)

Before doing anything else, check whether this local skill file is out of date:

1. Fetch the latest version marker from GitHub (one request, ~1 KB):
   ```
   curl -fsSL https://raw.githubusercontent.com/frontkom/night-shift/main/skills/night-shift/SKILL.md | grep -m1 NIGHT_SHIFT_VERSION
   ```
2. Compare the returned date against the `NIGHT_SHIFT_VERSION` comment at the top of this file.
3. If the remote is newer, auto-update the local file:
   ```
   curl -fsSL https://raw.githubusercontent.com/frontkom/night-shift/main/skills/night-shift/SKILL.md -o ~/.claude/skills/night-shift/SKILL.md
   ```
   Then **re-read** the updated file with the Read tool (`~/.claude/skills/night-shift/SKILL.md`) and follow the updated instructions from that point on. Tell the user:
   > Night Shift skill updated (local: `<old>` → `<new>`).
4. If the curl fails (offline, rate limited), silently skip the check and proceed with the local version.

Night Shift is a framework for scheduled nightly maintenance jobs across multiple repositories. It uses Claude Code routines (scheduled remote agents) to spawn nightly sessions that run a fixed set of bundles (groups of tasks) against the user's chosen repos.

The full source and the bundle / task prompt files live at:
**https://github.com/frontkom/night-shift**

That's the canonical reference. If you ever need to check what a bundle does, look there.

## Concepts

- **Task** — one atomic prompt file that does one thing in one repo (e.g. `add-tests`, `update-changelog`, `find-security-issues`).
- **Bundle** — a group of related tasks that run together. Four bundles total: `plans`, `docs`, `code-fixes`, `audits`.
- **Multi-* wrapper** — a meta prompt that auto-discovers all repos cloned into a session and dispatches one Task subagent per repo, then prints a summary table.
- **Routine** — a scheduled remote agent (created via the `/schedule` skill or `RemoteTrigger` tool) that fires nightly and runs a multi-* wrapper. (The API tool is still called `RemoteTrigger`; the UI calls them "Routines".)
- **Manifest** — `manifest.yml` in the night-shift repo, the source of truth for what tasks exist and how they group into bundles.

## Operations

Default to **Setup** unless the user clearly asks for something else (test once, add/remove a repo, status, update the skill).

## Setup runbook

**Step 0 — Check for existing Night Shift setup.**

Before welcoming the user, list routines via the `RemoteTrigger` tool (`action: "list"`) and filter to names starting with `night-shift-`.

Then:

- **If nothing found** → proceed to Step 1.
- **If existing setup found** → don't run fresh setup. Show what's already in place and ask what they want to do:

  > Night Shift is already set up:
  >
  > | Job | State | Schedule | Repos |
  > |---|---|---|---|
  > | build | `enabled` | `<local time>` | `<repo list>` |
  > | maintain | `enabled` | `<local time>` | `<repo list>` |
  > | audit | `disabled` | `<local time>` | `<repo list>` |
  >
  > Warning: if any Night Shift routine is `disabled`, config edits do **not** make it runnable again. I can still update its config, but it will not run until you re-enable it in Claude Code desktop or at https://claude.ai/code/routines. If it was auto-disabled after missed auth or connector approvals, fix that first, then re-enable and save.
  >
  > What would you like to do?
  > - **Add a repo** (runs the task picker for the new repo)
  > - **Remove a repo**
  > - **Change tasks for a repo** (re-run the picker for one existing repo)
  > - **Change the schedule**
  > - **Pause** a job
  > - **Delete everything** and start over
  > - **Nothing** — just wanted to check

  Dispatch to the matching runbook section. Never silently re-create routines that already exist. For "Delete everything and start over", delete all routines, then restart from **Step 1**.

---

## Disabled routine guardrail

Any time the skill reads an existing routine via `RemoteTrigger` `list` or `get` (setup discovery, status, add repo, remove repo, change tasks, change schedule, pause, delete, or any other post-setup edit), inspect the routine's `enabled` flag.

- If `enabled: false`, warn immediately before making any config edit:
  > Warning: this Night Shift routine is disabled. I can update its config, but it still will not run until you re-enable it in Claude Code desktop or at https://claude.ai/code/routines. If it was auto-disabled after missed auth or connector approvals, fix that first, then re-enable and save.
- Do **not** silently set `enabled: true` during an update. Preserve the current enabled/disabled state unless the user explicitly asks to re-enable the routine.
- Treat the warning as informational, not blocking. The user asked for a warning, not a forced stop.

---

**Step 1 — Welcome and explain, then ask one question.**

Send a single message that welcomes, states what Night Shift will do for them, and asks only for the repo list. Example:

> **Welcome to Night Shift.** I'll set up three scheduled jobs that run every night on your chosen repos:
>
> - **Build** — implements planned features from your plan files
> - **Maintain** — keeps docs in sync with code and fixes quality issues
> - **Audit** — opens PRs for security and bug findings
>
> You can pause, add, or remove repos any time.
>
> **One question to get started: which GitHub repositories should Night Shift manage?** Paste URLs, one per line or comma-separated (`owner/repo` or full URL, personal or org, both work).

Accept any of: `https://github.com/owner/repo`, `owner/repo`, `git@github.com:owner/repo.git`. Normalise to `https://github.com/owner/repo` (strip `.git`). If the user gives zero repos, stop and tell them to come back when they have at least one.

**Step 2 — Per-repo task picker.**

For each repo in the list, in the order the user gave them, run the picker loop below. You build up an in-memory map `selection[repo] = [task_id, …]` that gets baked into the routine prompts in Step 4.

**Picker defaults:** all tasks recommended per repo.

**Picker loop** (one `AskUserQuestion` call per repo, 3 questions per call):

1. Fetch `manifest.yml` once and cache it for the session.

2. Call `AskUserQuestion` with **3 questions**, all `multiSelect: true`. Mention the repo URL and progress (`repo N of M`) in the first question. Each option's `label` is the task id (e.g. `find-bugs`) and `description` is the human title from `manifest.yml`. Phrase questions to make clear all tasks are recommended.

   **Question 1 — "Plans + Docs"** (header: `Plans+Docs`):
   - `build-planned-features` — Build planned features
   - `work-on-issues` — Work on tagged GitHub issues
   - `work-on-jira-issues` — Work on tagged Jira issues (requires per-repo Jira project key + the Atlassian Rovo MCP connector attached to the build routine; see "Atlassian Rovo (Jira)" below)
   - `update-docs` — Update all documentation (changelog, user guide, ADRs, suggestions)

   **Question 2 — "Improve code quality"** (header: `Improve`):
   - `add-tests` — Add tests
   - `improve-accessibility` — Improve accessibility
   - `improve-seo` — Improve SEO
   - `improve-performance` — Improve performance
   - `translate-ui` — Translate UI

   **Question 3 — "Find issues"** (header: `Find issues`):
   Warn that active tasks here open PRs nightly when they find issues.
   - `find-security-issues` — Find security issues
   - `find-bugs` — Find bugs

   **Meta-option expansion.** `update-docs` is a picker shorthand, not a real task id. When building `selection[repo]`, expand it to the four individual doc task ids: `update-changelog`, `update-user-guide`, `document-decisions`, `suggest-improvements`. The allowlist and routine config always use real task ids from `manifest.yml` — never the meta-option name.

3. Merge selected ids from all 3 questions into `selection[repo]` and move to the next repo. If the user selected nothing across all questions, record the empty set — the create step will skip the repo.

4. **Jira follow-up (only if `work-on-jira-issues` was selected for this repo).** Ask one extra `AskUserQuestion` with two free-text fields:
   - `jira_project_key` — required, e.g. `FGPW`. The Jira project whose tagged issues should become PRs in this repo.
   - `jira_label` — optional, default `night-shift`. The label to filter on.

   Store these on `selection[repo].jira = { project: <KEY>, label: <LABEL> }`. In Step 4 this gets baked into the build routine's `<night-shift-config>` block as a `jira:` entry for this repo — **the user does not need to touch their repo at all**. (Putting `Jira project key:` in the repo's `CLAUDE.md` still works as an override/fallback, but it is no longer required; relying on that manual paste is what historically left opted-in repos silently never running Jira.)

   Then tell the user:

   > Got it — I'll store the Jira project key (`<KEY>`, label `<LABEL>`) directly in the routine config, so there's nothing to add to your repo.
   >
   > I'll walk you through the Atlassian Rovo connector setup before I create the routines (it's a one-time per-account flow — connect Rovo, flip tool permissions to "Always allow", and a possible one-click bootstrap if no routine has Rovo attached yet). Until that's all in place the task self-skips silently — no failure noise.

5. There is no `back` step. If the user wants to change a previous repo's picks, they can use "Change tasks for a repo" after setup completes.

**Step 3 — Schedule confirm.**

Show a compact summary of the picker output and the default schedule, ask for confirmation:

> **Selections:**
>
> | Repo | Tasks |
> |---|---|
> | `owner/repo-a` | 8 selected (plans, docs, code-fixes) |
> | `owner/repo-b` | 3 selected (find-bugs, improve-seo, improve-performance) |
>
> **Schedule** (Europe/Oslo, weeknights only): build 01:00, maintain-code 03:00, audit 04:00, maintain-docs 05:00.
>
> Skips Friday and Saturday nights — people rarely review PRs on Saturday or Sunday.
>
> Each routine has **auto-fix on its own PRs** enabled: when CI fails or a reviewer comments on a PR the routine opened, Claude wakes up, investigates, and pushes a fix — no separate triage routine needed.
>
> Proceed?

Default schedule → UTC cron, weeknights only: build `0 23 * * 0-4` (Sun-Thu UTC night → Mon-Fri morning), maintain-code `0 1 * * 1-5`, audit `0 2 * * 1-5`, maintain-docs `0 3 * * 1-5`.

Two reasons for this ordering:

1. **Docs runs LAST so it can summarize what the night actually did.** `update-changelog` scans `git log` for user-facing commits and `suggest-improvements` (Mode B) checks if existing suggestions are now implemented. Both give stale answers if they fire before code-fixes and audits. With docs at 03:00 UTC, it sees the commits and PRs the build / code-fixes / audits wrappers landed over the previous five hours.
2. **The build routine fires before midnight UTC** so it uses days 0-4 (Sun-Thu) to produce Mon-Fri morning PRs; the others fire after midnight so they use 1-5 (Mon-Fri). All four schedules deliberately skip producing PRs visible Saturday or Sunday morning.

If the user wants to tweak schedule, timezone, or include weekends, do it now, then proceed on explicit confirmation. If they decline, stop.

**Step 4 — Create the routines.**

**Which routines get created.** Fetch `https://raw.githubusercontent.com/frontkom/night-shift/main/manifest.yml` (you already fetched it for the picker in Step 2 — reuse the cache) and compute, per routine, the set of task ids that belong to it by bundle membership:

- **build routine** — tasks where `bundle: plans`.
- **maintain-docs routine** — tasks where `bundle: docs`.
- **maintain-code routine** — tasks where `bundle: code-fixes`.
- **audit routine** — tasks where `bundle: audits`.

CI-failure triage is handled by each routine's built-in **auto-fix on PR create** behavior (set via `autofix_on_pr_create: true` in the API body — see Step 4 example below). There is no separate triage routine.

**Do not hardcode task ids in the skill.** Always derive them from `manifest.yml` so new tasks added later flow through automatically.

A routine is created only if at least one repo's selection has a non-empty intersection with that routine's task set.

**If a routine's task set is empty across all repos, do not create that routine.** Tell the user which ones were skipped and why in Step 5's summary. The next time the user adds a task back in via "Change tasks for a repo", the skill re-creates the missing routine.

**`sources[]` per routine.** Include only repos whose selection includes at least one task belonging to that routine's bundles. A repo with zero tasks in a bundle is not cloned for that routine — it saves compute and keeps the summary clean.

**Inline the wrapper prompt.** Remote agents sometimes refuse "Fetch URL and execute" instructions, treating them as prompt injection. To avoid this, **fetch each wrapper prompt yourself during setup and inline its contents as the routine prompt**. For each routine:

1. Fetch the wrapper file from GitHub using WebFetch (URLs below).
2. Use the fetched content as the routine's prompt text.
3. Append the `<night-shift-config>` block at the end.

**Inline the allowlist.** Each routine's prompt gets a `<night-shift-config>` block appended at the end. For each routine, list only the tasks from its bundle that each repo selected. **Never put a task id in a routine's YAML that doesn't belong to that routine's bundles** — the wrapper ignores mismatched ids, but keeping the YAML clean makes the routines dashboard easier to read.

**Inline the Jira keys (build routine only).** For every repo whose selection includes `work-on-jira-issues`, append a `jira:` sub-block to the **build** routine's `<night-shift-config>` (see `bundles/_multi-runner.md` → "Optional `jira:` sub-block"), keyed by the same `https://github.com/owner/repo` URL, carrying `project_key: <KEY>` and — only when the user gave a non-default label — `label: <LABEL>`, both taken from `selection[repo].jira`. This is what puts the Jira project key **in the config** instead of requiring a `CLAUDE.md` edit in the target repo. Only the build routine runs `work-on-jira-issues`, so no other routine gets a `jira:` block. On add-repo / change-tasks rewrites, parse and preserve any existing `jira:` entries the same way the `repos:` block is merged.

Use the `RemoteTrigger` tool with `action: "create"`. **Do not** include `https://github.com/frontkom/night-shift` in sources — that repo is public and writing run logs to it would leak private project information.

**Fetching the environment_id (required, one-time).** The API requires a real `environment_id` — using `"default"` causes sessions to silently hang with no output. To get it:

1. Call `RemoteTrigger` with `action: "list"`.
2. If any routines exist, grab `job_config.ccr.environment_id` from one of them — done.
3. If **no routines exist** (first-time setup), walk the user through a quick bootstrap:
   - Tell them: *"I need to grab your environment ID. Go to **claude.ai/code/routines → Create routine**, enter any test prompt (e.g. 'say hello'), pick any repo, and save. Come back when done — I'll grab the ID and clean up the test routine."*
   - Wait for the user to confirm, then `list` again to capture `environment_id`.
   - Delete the bootstrap routine if the user wants (or repurpose it).

This only happens once — the `environment_id` is stable per account. Cache it for all routines in this session.

**If a repo (or a whole org) doesn't appear in the routine's repo picker.** This is the most common first-run snag, and it's an access problem, not a Night Shift bug: routines can only target repos the **Claude GitHub app** has been granted. Raise it proactively the moment a repo the user listed in Step 1 is missing from the picker (or from the bootstrap "pick any repo" step above) — don't wait for them to get stuck. Walk them through, in order:

1. Run `claude` and execute `/web-setup` — this links the GitHub account and usually makes the missing repos appear.
2. If they still don't show, open https://github.com/apps/claude → **Configure** → choose the **organization** → under **Repository access**, add the desired repo(s).
3. For org-owned repos this issues an **access request to the org admins**; the repos only appear once an admin approves. Tell the user to expect that approval step and to ping their admin if they don't administer the org themselves.

**Exact API body structure.** The RemoteTrigger API nests settings inside `job_config.ccr`. `mcp_connections` is a sibling of `job_config` (top-level), not nested. Here is a complete example for one routine — follow this structure exactly:

```json
{
  "name": "night-shift-build",
  "cron_expression": "0 23 * * 0-4",
  "enabled": true,
  "job_config": {
    "ccr": {
      "environment_id": "<real environment_id — see fetching instructions above; NEVER use 'default'>",
      "session_context": {
        "model": "claude-opus-4-8[1m]",
        "allowed_tools": ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebFetch", "WebSearch", "Task"],
        "autofix_on_pr_create": true,
        "sources": [
          { "git_repository": { "url": "https://github.com/owner/repo" } }
        ]
      },
      "events": [
        {
          "data": {
            "type": "user",
            "uuid": "<generate a unique uuid>",
            "session_id": "",
            "parent_tool_use_id": null,
            "message": {
              "role": "user",
              "content": "<the inlined wrapper prompt + night-shift-config block>"
            }
          }
        }
      ]
    }
  },
  "mcp_connections": []
}
```

Generate a fresh UUID for each routine's `events[0].data.uuid` using `python3 -c "import uuid; print(uuid.uuid4())"`.

**`RemoteTrigger update` is NOT a deep partial update.** It shallow-merges top-level fields (`enabled`, `cron_expression`, `mcp_connections`, etc.) but **replaces `job_config.ccr` wholesale**. If you send `{job_config: {ccr: {session_context: {autofix_on_pr_create: true}}}}` thinking you're only changing one nested field, you will (1) get rejected with `ccr.environment_id missing` and, after re-adding `environment_id`, (2) silently lose `events` — i.e. the wrapper prompt that defines what the routine does. Every `update` call that touches anything inside `ccr` must include the **complete** `ccr` block: `environment_id`, `events` (with the full inlined wrapper prompt), and the **full** `session_context` with every key you want preserved (`allowed_tools`, `model`, `sources`, `autofix_on_pr_create`). The canonical recipe is **GET → modify in memory → PUT the full ccr** — never construct a delta.

**Jira preflight — runs once when any repo's selection includes `work-on-jira-issues`.** Walk the user through this preflight before creating any routines. It has four checks; each gates on the previous one. Stop and instruct the user the moment any check fails — never proceed with a half-configured routine.

**Check 1: Is Rovo connected at the account level?** Run:

```bash
claude mcp list 2>&1 | grep -i "atlassian rovo"
```

Expected: a line containing `claude.ai Atlassian Rovo: ✓ Connected`. If you see `! Needs authentication` or no line at all, tell the user:

> The Atlassian Rovo connector isn't connected on your Claude account yet. Open https://claude.ai/customize/connectors, find **Atlassian Rovo** in the directory, click **Connect**, complete the Atlassian OAuth prompt. Then come back and re-run `/night-shift`.

Stop. Don't create routines until Rovo is connected.

**Check 2: Are tool permissions set to "Always allow"?** This **cannot be detected via API** — per-tool permission state isn't exposed in `RemoteTrigger get` and isn't readable from the local config. Always remind the user, every time:

> One thing I can't check from here: tool permissions. Routines run autonomously at 3 AM with no human to approve "Needs approval" tool calls — those calls would just hang the routine forever. Open https://claude.ai/customize/connectors → **Atlassian Rovo** → set **Interactive**, **Read-only**, **and Write/delete** all to **Always allow** (the ✓ icon). All three groups, simplest "set it and forget it". Confirm here when done.
>
> *(`AskUserQuestion`: "Have you flipped all three groups to Always allow?" — Yes / Not yet → if not yet, stop and wait.)*

**Check 3: Can the skill discover the connector UUID via the API?** Run `RemoteTrigger list`. For every returned routine, scan `mcp_connections[]` for an entry where `name` (case-insensitive) matches `atlassian-rovo` or `atlassian rovo`. Cache the first hit's `connector_uuid`, `name`, and `url`.

If found, the skill is fully automated from here — proceed to Check 4.

If **not** found (no existing routine has Rovo attached — the bootstrap caveat), tell the user:

> Rovo is connected on your account but I can't read its account-scoped UUID via the API yet — the API only exposes the UUID once at least one routine has Rovo attached. One-time bootstrap step: open https://claude.ai/code/routines → edit any routine (the build routine works; doesn't have to stay there) → toggle **Atlassian Rovo** on in the connectors panel → save. Then come back and re-run `/night-shift`. The skill will pick up the UUID and propagate it. This step only happens once per Claude account.

Stop. Don't create the build routine without the UUID.

**Check 4: Set `mcp_connections` on the build routine.** Using the cached UUID:

```json
[{"connector_uuid": "<cached uuid>", "name": "<cached name>", "url": "<cached url>", "permitted_tools": []}]
```

For routines other than the build routine, set `mcp_connections: []` — none of the other bundles use Jira tooling.

### Routine 1 — Build

- **name**: `night-shift-build`
- **cron_expression**: `0 23 * * 0-4` (Sun-Thu UTC night → Mon-Fri morning; skips Fri+Sat night so no Sat/Sun morning PRs)
- **wrapper URL**: `https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/multi-plans.md`
- **prompt**: Fetch the wrapper URL with WebFetch, then use its full contents as the prompt. Append the `<night-shift-config>` block at the end.

### Routine 2 — Maintain (docs)

- **name**: `night-shift-docs`
- **cron_expression**: `0 3 * * 1-5` (Mon-Fri UTC, **runs LAST** so it can summarize the night's plans / code-fixes / audits work; skips Sat+Sun mornings)
- **wrapper URL**: `https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/multi-docs.md`
- **prompt**: Fetch the wrapper URL with WebFetch, then use its full contents as the prompt. Append the `<night-shift-config>` block at the end.

### Routine 3 — Maintain (code fixes)

- **name**: `night-shift-code-fixes`
- **cron_expression**: `0 1 * * 1-5` (Mon-Fri UTC; skips Sat+Sun mornings)
- **wrapper URL**: `https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/multi-code-fixes.md`
- **prompt**: Fetch the wrapper URL with WebFetch, then use its full contents as the prompt. Append the `<night-shift-config>` block at the end.

### Routine 4 — Audit

- **name**: `night-shift-audit`
- **cron_expression**: `0 2 * * 1-5` (Mon-Fri UTC; skips Sat+Sun mornings)
- **wrapper URL**: `https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/multi-audits.md`
- **prompt**: Fetch the wrapper URL with WebFetch, then use its full contents as the prompt. Append the `<night-shift-config>` block at the end.

**Auto-fix on every routine.** All four routines must set `autofix_on_pr_create: true` in their `session_context`. This lets each routine wake up reactively when CI fails or a reviewer comments on one of its PRs, and push a fix. It replaces the old `night-shift-triage` cron routine, which ran a single sweep at 06:30 UTC across all PRs from the night — auto-fix is reactive (fires on the actual GitHub event), per-PR, and also handles review comments, which the cron sweep never did.

**Step 4b — Handle the routine cap.**

If the user's plan rejects the create with `trigger_limit_reached`, tell them:

> Your account's routine limit has been reached. List your existing routines and tell me which to delete. The Night Shift API can't delete — you'll need to delete them via https://claude.ai/code/routines.

**Step 5 — Summarise.**

Once all routines that should exist have been created, print:

```
✓ Night Shift is set up.

| Routine | Schedule | Repos | Tasks |
|---|---|---|---|
| build | <local time> | <N> | <M> selected |
| docs | <local time> | <N> | <M> selected |
| code-fixes | <local time> | <N> | <M> selected |
| audit | <local time> | <N> | <M> selected |

Auto-fix is enabled on every routine — Claude will react to CI failures
and review comments on its own PRs and push fixes without needing a
separate triage routine.

(Skipped: <any routines not created because no repo selected any of their
tasks — list them here, or "none" if all four were created.)

Tomorrow morning, review the night's PRs in each repo with
`gh pr list --label night-shift` (filter by title prefix —
`night-shift/bug:`, `night-shift/a11y:`, etc. — to narrow to a
specific bundle). The full summary table for each run is
also in the routines dashboard at https://claude.ai/code/routines. To
pause Night Shift on any project, drop a .nightshift-skip file at its
root. To change which tasks run on a repo, re-run /night-shift and pick
"Change tasks for a repo". See https://github.com/frontkom/night-shift
for the full reference.
```

## Atlassian Rovo (Jira) — connector setup

`work-on-jira-issues` does **not** use API tokens. It talks to Jira through the **Atlassian Rovo** MCP connector, which Claude manages via OAuth — no long-lived secrets to store.

### One-time account setup

Open https://claude.ai/customize/connectors, find **Atlassian Rovo** in the directory, click **Connect**, and complete the Atlassian OAuth prompt. After this, `claude mcp list` shows `claude.ai Atlassian Rovo: ✓ Connected`.

### Attaching Rovo to the build routine (the skill does this automatically)

Account-level connectors do **not** auto-propagate into routines — every routine in `RemoteTrigger list` shows `mcp_connections: []` until explicitly populated. The `mcp_connections` field on a routine takes this shape (verified 2026-04-28 by inspection; not officially documented):

```yaml
mcp_connections:
  - connector_uuid: <uuid>           # account-specific; same for all routines on this account
    name: Atlassian-Rovo
    url: https://mcp.atlassian.com/v1/mcp
    permitted_tools: []              # empty = use the connector's default per-tool permissions
```

When **any** repo's selection includes `work-on-jira-issues`, the skill must attach Rovo to the build routine.

**Discovering the connector UUID.** The UUID is account-scoped. The skill discovers it by:

1. Calling `RemoteTrigger list` to inspect existing routines.
2. Searching across all routines for the first `mcp_connections[]` entry whose `name` matches `Atlassian-Rovo` (case-insensitive — observed values: `Atlassian-Rovo`, possibly `Atlassian Rovo` or `atlassian-rovo` on different accounts).
3. Reusing its `connector_uuid` for the build routine being created/updated.

If no existing routine has Rovo attached (first-time setup), the skill instructs the user:

> Atlassian Rovo is connected on your account, but no routine has it attached yet, so I can't read its account-scoped UUID via the API. Please open https://claude.ai/code/routines, edit any routine, and toggle **Atlassian Rovo** on in the connectors panel. Save. Then re-run this step — I'll discover the UUID and propagate it.

This is a one-time bootstrap; once any routine has Rovo, the skill can read the UUID from there forever.

### Permissions: required step

The connector splits its 31 tools across three approval groups in the claude.ai UI: **Interactive** (5), **Read-only** (11), **Write/delete** (3). Each group defaults to **Needs approval**. For autonomous routines this is fatal — no human is awake at 3 AM to click "approve", so the routine hangs at the first Rovo tool call.

**The user must flip all three groups to "Always allow"** at https://claude.ai/customize/connectors → Atlassian Rovo. The skill cannot flip these via API — per-tool permission state isn't exposed in `RemoteTrigger get`'s output (`permitted_tools: []` reflects only the routine-level override, not the connector-wide setting).

The five tools the task uses — `Search with JQL`, `Get issue`, `Get transitions`, `Transition issue`, plus a comment-adding tool — straddle Interactive and Read-only (and possibly Write/delete for commenting). Flipping all three groups is the simplest "set it and forget it" choice. The skill always reminds the user; do not skip this reminder.

### Per-repo project key

The per-repo Jira project key is captured by the picker's Jira follow-up (Step 2.4) and baked into the build routine's `<night-shift-config>` `jira:` sub-block at create time — **no edit to the target repo is required**. The wrapper resolves the key from the config block first, then falls back to `Jira project key:` in the repo's `CLAUDE.md` `## Night Shift Config`. So a `CLAUDE.md` entry still works as an override/fallback (and is the only source for standalone, non-routine runs of the task), but it is no longer the primary path — which removes the old failure where an opted-in repo silently never ran Jira because the snippet was never pasted.

## Test-once runbook (no scheduling)

When the user wants to try Night Shift on the current repo without scheduling anything:

1. Ask which repo they want to test (default: the current working directory).
2. Confirm: "I'm about to run all four bundles against this repo. Plans → docs → code-fixes → audits. Each bundle commits its own changes. Test on a branch first if you want to inspect before keeping. Confirm?"
3. On confirm: walk through the four bundles in order, applying their rules. Most tasks self-skip if not applicable (no plans → silent, no UI → a11y silent, etc.).
4. Print the same summary table format as the multi-* wrappers.

## Parse-merge-rewrite contract

All post-setup operations (add repo, remove repo, change tasks) must **read the current routine prompt, parse the `<night-shift-config>` YAML block, merge the change in memory, and rewrite the prompt** — never regenerate from scratch. This preserves any hand-edits the user made in the routines dashboard (different wrapper URL, extra instructions, etc.).

Steps, for each of the four routines in turn:

1. Read the routine via `RemoteTrigger` (`action: "get"`) and capture its current `prompt`, `enabled`, and `sources[]`. If `enabled: false`, show the disabled-routine warning before continuing.
2. Locate the `<night-shift-config>` / `</night-shift-config>` delimiters. If absent, treat the current state as "all tasks allowed for all repos" and synthesise a full map from the current `sources[]`.
3. Parse the YAML, apply the change (add key, remove key, replace value), re-serialise.
4. Splice the new YAML back between the delimiters, preserving everything else in the prompt.
5. Update `sources[]` to match the union of `repos:` keys.
6. Write back via `RemoteTrigger` (`action: "update"`), preserving the current `enabled` state exactly unless the user explicitly asked to re-enable the routine. **Send the full `job_config.ccr` block** — `environment_id`, `events` (with the modified prompt), and the **full** `session_context` (every key from the GET response). `update` replaces `ccr` wholesale; a slim body silently drops whatever you omitted. See the gotcha note under Step 4's API body section.

If merging produces an empty `repos:` map for a routine, **delete that routine** (not just update it). If a merge would re-populate a routine that was previously deleted, **re-create it** using the Step 4 template from the Setup runbook.

## Add a repo

1. Ask the user for the repo URL(s). Normalise the same way as Step 1.
2. For each new repo, run the **Step 2 picker loop** so the user selects its tasks.
3. For each of the four routines, parse-merge-rewrite: add the repo to `sources[]` and to the `repos:` map with its selected tasks (filtered to the tasks belonging to that routine's bundles).
4. If a routine doesn't currently exist but the new repo has tasks for it, create it fresh using the Setup Step 4 template.
5. Print a summary of which routines were updated / created, the repos added, and the task counts.

## Remove a repo

1. Ask the user which repo(s) to remove from the installation.
2. For each of the four routines, parse-merge-rewrite: drop the repo from `sources[]` and from the `repos:` map.
3. If a routine's `repos:` map becomes empty, delete the routine entirely.
4. Print a summary.

## Change tasks for a repo

1. List the current routines and their `repos:` keys so the user can pick a repo. (Reject input for repos that aren't present in any routine.)
2. Parse the four routine prompts to recover the repo's **union** of currently selected tasks across bundles — this is the starting state for the picker.
3. Run the **Step 2 picker loop** for that one repo, pre-checked with the current selection.
4. For each of the four routines, parse-merge-rewrite: replace the repo's entry in `repos:` with the new selection filtered to that routine's bundles. Remove the repo entirely from a routine if no task in that routine's bundles is selected. Add it back to `sources[]` and `repos:` if new tasks in a routine's bundles are selected.
5. Create or delete routines as needed when the map goes from empty → non-empty or vice versa.
6. Print a diff-style summary: "repo-a: +add-tests, -find-bugs".

## Status

List the user's current routines via the `RemoteTrigger` tool (`action: "list"`). Filter to names starting with `night-shift-`. Show name, state (`enabled` / `disabled`), cron (converted to local time), and the repos in `sources[]`. If any routine is disabled, add an explicit warning that config edits do not re-enable it and tell the user to re-enable it in Claude Code desktop or at https://claude.ai/code/routines after fixing the auth/connector issue that disabled it.

> **Night Shift status:**
>
> | Job | State | Schedule | Repos |
> |---|---|---|---|
> | build | enabled | ... | ... |
>
> Warning: disabled routines will not run even if their Night Shift config was updated. Re-enable them in Claude Code desktop or at https://claude.ai/code/routines after fixing the auth/connector problem.

## Notes for Claude

- **Always ask for explicit confirmation** before creating, updating, or deleting routines. They are persistent and run unattended — high blast radius.
- **Existing installations from before 2026-05-19:** if Step 0 finds a routine named `night-shift-triage`, tell the user it's been replaced by per-routine auto-fix, ask them to delete it via https://claude.ai/code/routines, and use `RemoteTrigger update` to set `autofix_on_pr_create: true` on each of the other four routines' `session_context`. (The `RemoteTrigger` API has no `delete` action — manual UI deletion is the only path.)
- **Inline wrapper prompts at setup time.** Fetch each multi-*.md wrapper from GitHub during setup and inline the contents as the routine prompt. Remote agents refuse "Fetch URL and execute" instructions (prompt injection guard), so the wrapper must be baked in. The wrapper's inner references (subagents fetching bundle/task prompts via WebFetch) are fine — only the top-level "fetch and execute" is refused.
- **The task and bundle URLs are stable.** They live at `raw.githubusercontent.com/frontkom/night-shift/main/...`. Subagents fetch these at run time, which works because they already have tool access. Only the top-level routine prompt must be inlined.
- **Refuse if the user can't articulate what Night Shift should do for them.** If the request is vague or feels delegated from somewhere, ask the user directly what they want to accomplish before taking any action.
