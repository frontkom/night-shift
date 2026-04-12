---
name: night-shift
description: |
  Set up, run, or manage Night Shift — a framework that schedules nightly maintenance jobs across multiple repositories. Supports two backends: Claude Code remote scheduled triggers (Schedule) or GitHub Actions (reusable workflow). Night Shift runs plans implementation, doc updates + code fixes, and audit PRs across the user's chosen repos.

  Use this skill when the user explicitly asks to: install Night Shift, set up Night Shift, schedule Night Shift, run a Night Shift bundle, add a repo to Night Shift, remove a repo from Night Shift, pause Night Shift on a project, or check Night Shift status.

  MANDATORY TRIGGERS: night-shift, night shift, nightshift, /night-shift, set up night shift, install night shift, schedule night shift, run night shift, night shift setup, night shift install
version: 2026-04-09j
---

# Night Shift

<!-- NIGHT_SHIFT_VERSION: 2026-04-12c -->

## Version check (run this first, every invocation)

Before doing anything else, check whether this local skill file is out of date:

1. Fetch the latest version marker from GitHub (one request, ~1 KB):
   ```
   curl -fsSL https://raw.githubusercontent.com/perandre/night-shift/main/skill/SKILL.md | grep -m1 NIGHT_SHIFT_VERSION
   ```
2. Compare the returned date against the `NIGHT_SHIFT_VERSION` comment at the top of this file.
3. If the remote is newer, auto-update the local file:
   ```
   curl -fsSL https://raw.githubusercontent.com/perandre/night-shift/main/skill/SKILL.md -o ~/.claude/skills/night-shift/SKILL.md
   ```
   Then **re-read** the updated file with the Read tool (`~/.claude/skills/night-shift/SKILL.md`) and follow the updated instructions from that point on. Tell the user:
   > Night Shift skill updated (local: `<old>` → `<new>`).
4. If the curl fails (offline, rate limited), silently skip the check and proceed with the local version.

Night Shift is a framework for scheduled nightly maintenance jobs across multiple repositories. It uses Claude Code's remote scheduled triggers to spawn nightly sessions that run a fixed set of bundles (groups of tasks) against the user's chosen repos.

The full source and the bundle / task prompt files live at:
**https://github.com/perandre/night-shift**

That's the canonical reference. If you ever need to check what a bundle does, look there.

## Concepts

- **Task** — one atomic prompt file that does one thing in one repo (e.g. `add-tests`, `update-changelog`, `find-security-issues`).
- **Bundle** — a group of related tasks that run together. Four bundles total: `plans`, `docs`, `code-fixes`, `audits`.
- **Multi-* wrapper** — a meta prompt that auto-discovers all repos cloned into a session and dispatches one Task subagent per repo, then prints a summary table.
- **Trigger** — a scheduled remote agent (created via the `/schedule` skill or `RemoteTrigger` tool) that fires nightly and runs a multi-* wrapper.
- **Manifest** — `manifest.yml` in the night-shift repo, the source of truth for what tasks exist and how they group into bundles.

## Operations

Default to **Setup** unless the user clearly asks for something else (test once, add/remove a repo, status, update the skill).

## Setup runbook

**Step 0 — Check for existing Night Shift setup (both backends).**

Before welcoming the user, check both backends:

1. **Schedule:** List scheduled triggers via the `RemoteTrigger` tool (`action: "list"`) and filter to names starting with `night-shift-`.
2. **GitHub Actions:** Search for `.github/workflows/night-shift.yml` in sibling directories and common locations (`~/Sites`, `~/Projects`, `~/Code`, `~/repos`, `~/dev`). A repo has Night Shift via GHA if this file exists and references `perandre/night-shift`.

Then:

- **If nothing found (no triggers, no workflow files)** → proceed to Step 0b (choose backend).
- **If existing setup found** → don't run fresh setup. Show what's already in place across both backends and ask what they want to do:

  > Night Shift is already set up:
  >
  > **Schedule (remote triggers):** *(if any triggers found)*
  > | Job | Schedule | Repos |
  > |---|---|---|
  > | build | `<local time>` | `<repo list>` |
  > | maintain | `<local time>` | `<repo list>` |
  > | audit | `<local time>` | `<repo list>` |
  >
  > **GitHub Actions:** *(if any workflow files found)*
  > | Repo | Schedule | Tasks |
  > |---|---|---|
  > | `owner/repo-a` | `<cron>` | `<N>` tasks |
  >
  > What would you like to do?
  > - **Add a repo** (runs the task picker for the new repo)
  > - **Remove a repo**
  > - **Change tasks for a repo** (re-run the picker for one existing repo)
  > - **Change the schedule**
  > - **Pause** a job / workflow
  > - **Delete everything** and start over (re-choose backend)
  > - **Add GitHub Actions** to more repos (if using Schedule and want to expand with GHA)
  > - **Nothing** — just wanted to check

  Dispatch to the matching runbook section based on which backend the repo uses. For "Add a repo", ask which backend to use (or infer from context — e.g., if the user only has one backend set up, use that). Never silently re-create triggers that already exist. For "Delete everything and start over", delete all triggers and workflow files, then restart from **Step 0b** (choose backend) so the user can pick fresh.

**Step 0b — Choose backend.**

Ask the user how they want Night Shift to run:

> **How should Night Shift run?**
>
> - **Schedule** — runs via your Claude account's remote triggers (no API key needed, included in your subscription)
> - **GitHub Actions** — runs on GitHub's infrastructure (requires an `ANTHROPIC_API_KEY` in your repo/org secrets)

- If **Schedule** → continue to Step 1 below (existing flow, unchanged).
- If **GitHub Actions** → jump to the **GitHub Actions setup runbook** section below.

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

For each repo in the list, in the order the user gave them, run the picker loop below. You build up an in-memory map `selection[repo] = [task_id, …]` that gets baked into the trigger prompts in Step 4.

**Picker defaults:** all tasks recommended per repo.

**Picker loop** (one `AskUserQuestion` call per repo, 3 questions per call):

1. Fetch `manifest.yml` once and cache it for the session.

2. Call `AskUserQuestion` with **3 questions**, all `multiSelect: true`. Mention the repo URL and progress (`repo N of M`) in the first question. Each option's `label` is the task id (e.g. `find-bugs`) and `description` is the human title from `manifest.yml`. Phrase questions to make clear all tasks are recommended.

   **Question 1 — "Plans + Docs"** (header: `Plans+Docs`):
   - `build-planned-features` — Build planned features
   - `work-on-issues` — Work on tagged GitHub issues
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

   **Meta-option expansion.** `update-docs` is a picker shorthand, not a real task id. When building `selection[repo]`, expand it to the five individual doc task ids: `update-changelog`, `update-user-guide`, `document-decisions`, `suggest-improvements`, `weekly-digest`. The allowlist and trigger config always use real task ids from `manifest.yml` — never the meta-option name.

3. Merge selected ids from all 3 questions into `selection[repo]` and move to the next repo. If the user selected nothing across all questions, record the empty set — the create step will skip the repo.

4. There is no `back` step. If the user wants to change a previous repo's picks, they can use "Change tasks for a repo" after setup completes.

**Step 3 — Schedule confirm.**

Show a compact summary of the picker output and the default schedule, ask for confirmation:

> **Selections:**
>
> | Repo | Tasks |
> |---|---|
> | `owner/repo-a` | 8 selected (plans, docs, code-fixes) |
> | `owner/repo-b` | 3 selected (find-bugs, improve-seo, improve-performance) |
>
> **Schedule** (Europe/Oslo): build 01:00, maintain 03:00, audit 05:00.
>
> Proceed?

Default schedule → UTC cron: build `0 23 * * *`, maintain `0 1 * * *`, audit `0 3 * * *`. If the user wants to tweak schedule or timezone, do it now, then proceed on explicit confirmation. If they decline, stop.

**Step 4 — Create the triggers.**

**Which triggers get created.** Fetch `https://raw.githubusercontent.com/perandre/night-shift/main/manifest.yml` (you already fetched it for the picker in Step 2 — reuse the cache) and compute, per trigger, the set of task ids that belong to it by bundle membership:

- **build trigger** — tasks where `bundle: plans`.
- **maintain trigger** — tasks where `bundle: docs` OR `bundle: code-fixes`.
- **audit trigger** — tasks where `bundle: audits`.

**Do not hardcode task ids in the skill.** Always derive them from `manifest.yml` so new tasks added later flow through automatically.

A trigger is created only if at least one repo's selection has a non-empty intersection with that trigger's task set.

**If a trigger's task set is empty across all repos, do not create that trigger.** This saves a slot against the 3-trigger cap. Tell the user which ones were skipped and why in Step 5's summary. The next time the user adds a task back in via "Change tasks for a repo", the skill re-creates the missing trigger.

**`sources[]` per trigger.** Include only repos whose selection includes at least one task belonging to that trigger's bundles. A repo with zero tasks in a bundle is not cloned for that trigger — it saves compute and keeps the summary clean.

**Inline the wrapper prompt.** Remote agents sometimes refuse "Fetch URL and execute" instructions, treating them as prompt injection. To avoid this, **fetch each wrapper prompt yourself during setup and inline its contents as the trigger prompt**. For each trigger:

1. Fetch the wrapper file from GitHub using WebFetch (URLs below).
2. Use the fetched content as the trigger's prompt text.
3. Append the `<night-shift-config>` block at the end.

**Inline the allowlist.** Each trigger's prompt gets a `<night-shift-config>` block appended at the end. For the maintain trigger, list only the docs+code-fixes tasks each repo selected. For the audit trigger, list only the audit tasks each repo selected. **Never put a task id in a trigger's YAML that doesn't belong to that trigger's bundles** — the wrapper ignores mismatched ids, but keeping the YAML clean makes the trigger dashboard easier to read.

Use the `RemoteTrigger` tool with `action: "create"`. **Do not** include `https://github.com/perandre/night-shift` in sources — that repo is public and writing run logs to it would leak private project information.

**Exact API body structure.** The RemoteTrigger API nests settings inside `job_config.ccr`. Here is a complete example for one trigger — follow this structure exactly:

```json
{
  "name": "night-shift-build",
  "cron_expression": "0 23 * * *",
  "enabled": true,
  "environment_id": "default",
  "job_config": {
    "ccr": {
      "session_context": {
        "model": "claude-opus-4-6[1m]",
        "allowed_tools": ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebFetch", "WebSearch"],
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
  }
}
```

Generate a fresh UUID for each trigger's `events[0].data.uuid` using `python3 -c "import uuid; print(uuid.uuid4())"`.

### Trigger 1 — Build

- **name**: `night-shift-build`
- **cron_expression**: `0 23 * * *`
- **wrapper URL**: `https://raw.githubusercontent.com/perandre/night-shift/main/bundles/multi-plans.md`
- **prompt**: Fetch the wrapper URL with WebFetch, then use its full contents as the prompt. Append the `<night-shift-config>` block at the end.

### Trigger 2 — Maintain

- **name**: `night-shift-maintain`
- **cron_expression**: `0 1 * * *`
- **wrapper URL**: `https://raw.githubusercontent.com/perandre/night-shift/main/bundles/multi-docs-and-code-fixes.md`
- **prompt**: Fetch the wrapper URL with WebFetch, then use its full contents as the prompt. Append the `<night-shift-config>` block at the end.

### Trigger 3 — Audit

- **name**: `night-shift-audit`
- **cron_expression**: `0 3 * * *`
- **wrapper URL**: `https://raw.githubusercontent.com/perandre/night-shift/main/bundles/multi-audits.md`
- **prompt**: Fetch the wrapper URL with WebFetch, then use its full contents as the prompt. Append the `<night-shift-config>` block at the end.

**Step 4b — Handle the trigger cap.**

If the user's plan rejects the create with `trigger_limit_reached`, tell them:

> Your account has a 3-trigger cap. List your existing scheduled triggers and tell me which to delete. The Night Shift API can't delete — you'll need to delete them via https://claude.ai/code/scheduled.

The cap appears to count enabled triggers. Disabled ones may also count, depending on plan tier.

**Step 5 — Summarise.**

Once all triggers that should exist have been created, print:

```
✓ Night Shift is set up.

| Job | Schedule | Repos | Tasks |
|---|---|---|---|
| build | <local time> | <N> | <M> selected |
| maintain | <local time> | <N> | <M> selected |
| audit | <local time> | <N> | <M> selected |

(Skipped: <any triggers not created because no repo selected any of their
tasks — list them here, or "none" if all three were created.)

Tomorrow morning, check docs/NIGHTSHIFT-HISTORY.md in each repo for what
happened. The full summary table for each run is also in the trigger
dashboard at https://claude.ai/code/scheduled. To pause Night Shift on
any project, drop a .nightshift-skip file at its root. To change which
tasks run on a repo, re-run /night-shift and pick "Change tasks for a
repo". See https://github.com/perandre/night-shift for the full reference.
```

## Test-once runbook (no scheduling)

When the user wants to try Night Shift on the current repo without scheduling anything:

1. Ask which repo they want to test (default: the current working directory).
2. Confirm: "I'm about to run all four bundles against this repo. Plans → docs → code-fixes → audits. Each bundle commits its own changes. Test on a branch first if you want to inspect before keeping. Confirm?"
3. On confirm: walk through the four bundles in order, applying their rules. Most tasks self-skip if not applicable (no plans → silent, no UI → a11y silent, etc.).
4. Append a row per bundle to `docs/NIGHTSHIFT-HISTORY.md` and commit.
5. Print the same summary table format as the multi-* wrappers.

## Parse-merge-rewrite contract

All post-setup operations (add repo, remove repo, change tasks) must **read the current trigger prompt, parse the `<night-shift-config>` YAML block, merge the change in memory, and rewrite the prompt** — never regenerate from scratch. This preserves any hand-edits the user made in the Claude Code dashboard (different wrapper URL, extra instructions, etc.).

Steps, for each of the three triggers in turn:

1. Read the trigger's current `prompt` via `RemoteTrigger` (`action: "get"`).
2. Locate the `<night-shift-config>` / `</night-shift-config>` delimiters. If absent, treat the current state as "all tasks allowed for all repos" and synthesise a full map from the current `sources[]`.
3. Parse the YAML, apply the change (add key, remove key, replace value), re-serialise.
4. Splice the new YAML back between the delimiters, preserving everything else in the prompt.
5. Update `sources[]` to match the union of `repos:` keys.
6. Write back via `RemoteTrigger` (`action: "update"`).

If merging produces an empty `repos:` map for a trigger, **delete that trigger** (not just update it). If a merge would re-populate a trigger that was previously deleted, **re-create it** using the Step 4 template from the Setup runbook.

## Add a repo

1. Ask the user for the repo URL(s). Normalise the same way as Step 1.
2. For each new repo, run the **Step 2 picker loop** so the user selects its tasks.
3. For each of the three triggers, parse-merge-rewrite: add the repo to `sources[]` and to the `repos:` map with its selected tasks (filtered to the tasks belonging to that trigger's bundles).
4. If a trigger doesn't currently exist but the new repo has tasks for it, create it fresh using the Setup Step 4 template.
5. Print a summary of which triggers were updated / created, the repos added, and the task counts.

## Remove a repo

1. Ask the user which repo(s) to remove from the installation.
2. For each of the three triggers, parse-merge-rewrite: drop the repo from `sources[]` and from the `repos:` map.
3. If a trigger's `repos:` map becomes empty, delete the trigger entirely.
4. Print a summary.

## Change tasks for a repo

1. List the current triggers and their `repos:` keys so the user can pick a repo. (Reject input for repos that aren't present in any trigger.)
2. Parse the three trigger prompts to recover the repo's **union** of currently selected tasks across bundles — this is the starting state for the picker.
3. Run the **Step 2 picker loop** for that one repo, pre-checked with the current selection.
4. For each of the three triggers, parse-merge-rewrite: replace the repo's entry in `repos:` with the new selection filtered to that trigger's bundles. Remove the repo entirely from a trigger if no task in that trigger's bundles is selected. Add it back to `sources[]` and `repos:` if new tasks in a trigger's bundles are selected.
5. Create or delete triggers as needed when the map goes from empty → non-empty or vice versa.
6. Print a diff-style summary: "repo-a: +add-tests, -find-bugs".

## Status

Check both backends and show a unified view:

**Schedule backend:** List the user's current scheduled triggers via the `RemoteTrigger` tool (`action: "list"`). Filter to names starting with `night-shift-`. Show name, cron (converted to local time), and the repos in `sources[]`.

**GitHub Actions backend:** Search for `.github/workflows/night-shift.yml` in sibling directories of the current working directory and common locations (`~/Sites`, `~/Projects`, `~/Code`, `~/repos`, `~/dev`). For each found, parse the `tasks:` value. Show repo path, cron schedule, and task count.

Present both in a single summary:

> **Night Shift status:**
>
> **Schedule (remote triggers):**
> | Job | Schedule | Repos |
> |---|---|---|
> | build | ... | ... |
>
> **GitHub Actions (workflow files):**
> | Repo | Schedule | Tasks |
> |---|---|---|
> | owner/repo-a | 01:00 UTC weeknights | 8 tasks |

---

## GitHub Actions setup runbook

This runbook is used when the user chooses **GitHub Actions** in Step 0b. The Schedule backend (above) remains completely separate — this section does not touch remote triggers.

**GA-Step 1 — Welcome and explain, then ask for repos.**

> **Welcome to Night Shift (GitHub Actions mode).** I'll generate a workflow file for each repo and create PRs on GitHub.
>
> **Prerequisites:**
> - **GitHub CLI** (`gh`) — installed and authenticated (`gh auth status` to check)
> - **`ANTHROPIC_API_KEY`** in your GitHub **org secrets** (one key covers all repos)
>   Org Settings → Secrets and variables → Actions → New organization secret
>   *(Or per-repo if you prefer: repo Settings → Secrets and variables → Actions)*
>
> That's it — no other tools or libraries needed. The workflow installs everything it needs on the runner automatically.
>
> **Which GitHub repositories should Night Shift manage?** Paste URLs, one per line or comma-separated.

Before proceeding, verify `gh` is available and authenticated:
```bash
gh auth status
```
If not installed, tell the user to install it (`brew install gh` on macOS, or see https://cli.github.com) and authenticate with `gh auth login`. Do not proceed until `gh` is working.

Accept any of: `https://github.com/owner/repo`, `owner/repo`, `git@github.com:owner/repo.git`. Normalise to `https://github.com/owner/repo`.

**GA-Step 2 — Per-repo task picker.**

Use the exact same picker as the Schedule backend's Step 2 (same questions, same format, same meta-option expansion). Build `selection[repo] = [task_id, …]`.

**GA-Step 3 — Schedule confirm.**

Show the same compact summary as the Schedule backend's Step 3, but adapted:

> **Selections:**
>
> | Repo | Tasks |
> |---|---|
> | `owner/repo-a` | 8 selected |
> | `owner/repo-b` | 3 selected |
>
> **Schedule:** `0 1 * * 1-5` (weeknights 01:00 UTC). Adjust?
>
> Each repo gets a `.github/workflows/night-shift.yml` that calls the
> shared reusable workflow at `perandre/night-shift`.
>
> Proceed?

**GA-Step 4 — Generate workflow files and create PRs.**

For each repo in `selection`:

1. Build the task list string: join `selection[repo]` with commas.

2. Generate the caller workflow file from the template at `https://raw.githubusercontent.com/perandre/night-shift/main/github-actions/caller-template.yml`. Fetch it once and cache. Replace the `tasks:` value with the repo's selected tasks. Replace the `cron:` value if the user customised the schedule. Replace `COMMIT_SHA` in the `uses:` line with the latest commit SHA from the night-shift repo (run `git ls-remote https://github.com/perandre/night-shift HEAD` to get it). This pins the workflow to a known-good version for supply-chain safety.

3. Create a PR on GitHub using the `gh` CLI — **no local clone needed**:
   ```bash
   # Create a new branch and commit the workflow file directly on GitHub
   gh api repos/OWNER/REPO/git/refs/heads/main -q '.object.sha'  # get base SHA
   gh api repos/OWNER/REPO/git/trees -f base_tree=BASE_SHA \
     -f 'tree[][path]=.github/workflows/night-shift.yml' \
     -f 'tree[][mode]=100644' \
     -f 'tree[][type]=blob' \
     -f 'tree[][content]=<FILE_CONTENT>'  # create tree
   gh api repos/OWNER/REPO/git/commits \
     -f message="Add Night Shift workflow" \
     -f 'tree=TREE_SHA' -f 'parents[]=BASE_SHA'  # create commit
   gh api repos/OWNER/REPO/git/refs -f ref=refs/heads/night-shift-setup \
     -f sha=COMMIT_SHA  # create branch
   gh pr create --repo OWNER/REPO --head night-shift-setup \
     --title "Add Night Shift nightly maintenance" \
     --body "Adds a GitHub Actions workflow that runs Night Shift nightly."
   ```
   This works for any repo the user has push access to, without needing it cloned locally.

**GA-Step 5 — Summarise.**

```
Night Shift (GitHub Actions) is ready.

PRs created:
  - owner/repo-a#123 — Night Shift (8 tasks)
  - owner/repo-b#124 — Night Shift (3 tasks)

Next steps:
  1. Review and merge the PRs
  2. Add ANTHROPIC_API_KEY to your GitHub org secrets (one key covers all repos)
     (Org Settings → Secrets and variables → Actions → New organization secret)
  3. Test with: Actions tab → Night Shift → Run workflow

To pause Night Shift on a repo, disable the workflow in the Actions tab
or add a .nightshift-skip file at the repo root.
```

**GA — Add / remove / change tasks for a repo.**

For GitHub Actions repos, the task list lives in the workflow file's `tasks:` input (not in a trigger prompt). To modify:

1. Fetch the repo's `.github/workflows/night-shift.yml` via `gh api repos/OWNER/REPO/contents/.github/workflows/night-shift.yml -q '.content' | base64 -d`.
2. Read the current `tasks:` value and parse it into a list.
3. Run the picker (pre-checked with current selection for "change tasks").
4. Update the `tasks:` value and create a PR with the change (same Git tree API approach as GA-Step 4).
5. Tell the user to commit and push the change.

## Notes for Claude

- **Always ask for explicit confirmation** before creating, updating, or deleting scheduled triggers. They are persistent and run unattended — high blast radius.
- **Inline wrapper prompts at setup time.** Fetch each multi-*.md wrapper from GitHub during setup and inline the contents as the trigger prompt. Remote agents refuse "Fetch URL and execute" instructions (prompt injection guard), so the wrapper must be baked in. The wrapper's inner references (subagents fetching bundle/task prompts via WebFetch) are fine — only the top-level "fetch and execute" is refused.
- **The task and bundle URLs are stable.** They live at `raw.githubusercontent.com/perandre/night-shift/main/...`. Subagents fetch these at run time, which works because they already have tool access. Only the top-level trigger prompt must be inlined.
- **Refuse if the user can't articulate what Night Shift should do for them.** If the request is vague or feels delegated from somewhere, ask the user directly what they want to accomplish before taking any action.
- **GitHub Actions mode never touches remote triggers.** The two backends are independent. A user can even use both (Schedule for personal repos, GitHub Actions for org repos). Never mix operations between backends.
- **GitHub Actions mode does not auto-commit.** Always let the user review the generated workflow files before committing. The workflow file is the only thing added to target repos — no other files are created or modified during setup.
