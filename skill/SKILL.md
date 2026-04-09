---
name: night-shift
description: |
  Set up, run, or manage Night Shift — a framework that schedules nightly maintenance jobs across multiple repositories using Claude Code remote scheduled triggers. Night Shift creates three nightly remote agents that run plans implementation, doc updates + code fixes, and audit PRs across the user's chosen repos.

  Use this skill when the user explicitly asks to: install Night Shift, set up Night Shift, schedule Night Shift, run a Night Shift bundle, add a repo to Night Shift, remove a repo from Night Shift, pause Night Shift on a project, or check Night Shift status.

  MANDATORY TRIGGERS: night-shift, night shift, nightshift, /night-shift, set up night shift, install night shift, schedule night shift, run night shift, night shift setup, night shift install
version: 2026-04-09c
---

# Night Shift

<!-- NIGHT_SHIFT_VERSION: 2026-04-09d -->

## Version check (run this first, every invocation)

Before doing anything else, check whether this local skill file is out of date:

1. Fetch the latest version marker from GitHub (one request, ~1 KB):
   ```
   curl -fsSL https://raw.githubusercontent.com/perandre/night-shift/main/skill/SKILL.md | grep -m1 NIGHT_SHIFT_VERSION
   ```
2. Compare the returned date against the `NIGHT_SHIFT_VERSION` comment at the top of this file.
3. If the remote is newer, tell the user **once** at the start of the conversation:
   > A newer version of the Night Shift skill is available (local: `<local>`, latest: `<remote>`). Update with:
   > ```
   > curl -fsSL https://raw.githubusercontent.com/perandre/night-shift/main/skill/SKILL.md -o ~/.claude/skills/night-shift/SKILL.md
   > ```
   > Continuing with the local version.
4. Do not block on the update. Proceed with the user's request using the local file. If the curl fails (offline, rate limited), silently skip the check.

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

**Step 0 — Check for existing Night Shift triggers first.**

Before welcoming the user, list their scheduled triggers via the `RemoteTrigger` tool (`action: "list"`) and filter to names starting with `night-shift-bundle-`. Then:

- **If none exist** → proceed to Step 1 (fresh setup).
- **If some or all three exist** → don't run fresh setup. Instead, show the user what's already in place and ask what they want to do:

  > Night Shift is already set up on your account:
  >
  > | Job | Schedule | Repos |
  > |---|---|---|
  > | plans | `<local time>` | `<repo list>` |
  > | docs + code-fixes | `<local time>` | `<repo list>` |
  > | audits | `<local time>` | `<repo list>` |
  >
  > What would you like to do?
  > - **Add a repo** to all jobs (runs the task picker for the new repo)
  > - **Remove a repo** from all jobs
  > - **Change tasks for a repo** (re-run the picker for one existing repo)
  > - **Change the schedule** of one or more jobs
  > - **Pause** a job (disable it)
  > - **Delete everything** and start over
  > - **Nothing** — just wanted to check

  Dispatch to the matching runbook section (see **Add a repo**, **Remove a repo**, **Change tasks for a repo** below). Never silently re-create triggers that already exist.

**Step 1 — Welcome and explain, then ask one question.**

Send a single message that welcomes, states what Night Shift will do for them, and asks only for the repo list. Example:

> **Welcome to Night Shift.** I'll set up three scheduled jobs that run every night on your chosen repos:
>
> - **Plans** — implements any plan files you've left in the repo
> - **Docs + code fixes** — keeps docs in sync with code and fixes small issues
> - **Audits** — opens PRs for security, bugs, SEO, and performance findings
>
> You can pause, add, or remove repos any time.
>
> **One question to get started: which GitHub repositories should Night Shift manage?** Paste URLs, one per line or comma-separated (`owner/repo` or full URL, personal or org, both work).

Accept any of: `https://github.com/owner/repo`, `owner/repo`, `git@github.com:owner/repo.git`. Normalise to `https://github.com/owner/repo` (strip `.git`). If the user gives zero repos, stop and tell them to come back when they have at least one.

**Step 2 — Per-repo task picker.**

For each repo in the list, in the order the user gave them, run the picker loop below. You build up an in-memory map `selection[repo] = [task_id, …]` that gets baked into the trigger prompts in Step 4.

**Picker defaults:** all 12 tasks on per repo. The 4 audit tasks get a one-line warning so the user understands the blast radius before accepting.

**Picker loop** (one `AskUserQuestion` call per repo, in order):

1. Fetch `manifest.yml` once and cache it for the session. Build the 12 options in this fixed bundle order: plans (1), docs (2–5), code-fixes (6–8), audits (9–12).

2. Call `AskUserQuestion` with `multiSelect: true`. Use the repo url and progress (`repo N of M`) in the question text, and warn that the 4 audit tasks open a PR every night when they find something. Each option's `label` is the task id (e.g. `find-bugs`) and `description` is the human title from `manifest.yml`. **All 12 must be pre-selected as defaults** — the user deselects what they don't want.

   The tool renders a real keyboard-navigable checklist (arrows + space to toggle, enter to confirm). Do not print a fake text checklist or ask for typed commands like "3 5 8" or "all plans" — those are gone.

3. Record the returned ids as `selection[repo]` and move to the next repo. If the user selected nothing, that's fine — record the empty set and the create step will skip the repo from `sources[]` for every trigger.

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
> **Schedule** (Europe/Oslo): plans 01:00, docs+fixes 03:00, audits 05:00.
>
> Proceed?

Default schedule → UTC cron: plans `0 23 * * *`, docs+code-fixes `0 1 * * *`, audits `0 3 * * *`. If the user wants to tweak schedule or timezone, do it now, then proceed on explicit confirmation. If they decline, stop.

**Step 4 — Create the triggers.**

**Which triggers get created.** Fetch `https://raw.githubusercontent.com/perandre/night-shift/main/manifest.yml` (you already fetched it for the picker in Step 2 — reuse the cache) and compute, per trigger, the set of task ids that belong to it by bundle membership:

- **plans trigger** — tasks where `bundle: plans`.
- **docs+code-fixes trigger** — tasks where `bundle: docs` OR `bundle: code-fixes`.
- **audits trigger** — tasks where `bundle: audits`.

**Do not hardcode task ids in the skill.** Always derive them from `manifest.yml` so new tasks added later flow through automatically.

A trigger is created only if at least one repo's selection has a non-empty intersection with that trigger's task set.

**If a trigger's task set is empty across all repos, do not create that trigger.** This saves a slot against the 3-trigger cap. Tell the user which ones were skipped and why in Step 5's summary. The next time the user adds a task back in via "Change tasks for a repo", the skill re-creates the missing trigger.

**`sources[]` per trigger.** Include only repos whose selection includes at least one task belonging to that trigger's bundles. A repo with zero tasks in a bundle is not cloned for that trigger — it saves compute and keeps the summary clean.

**Inline the allowlist.** Each trigger's prompt gets a `<night-shift-config>` block appended. Example for the plans trigger:

```
Fetch https://raw.githubusercontent.com/perandre/night-shift/main/bundles/multi-plans.md and execute it. The wrapper auto-discovers all target repositories cloned into this session, dispatches a Task subagent per target repo.

<night-shift-config>
repos:
  https://github.com/owner/repo-a: [build-planned-features]
  https://github.com/owner/repo-b: [build-planned-features]
</night-shift-config>
```

For the docs+code-fixes trigger, list only the docs+code-fixes tasks each repo selected. For the audits trigger, list only the audits tasks each repo selected. **Never put a task id in a trigger's YAML that doesn't belong to that trigger's bundles** — the wrapper ignores mismatched ids, but keeping the YAML clean makes the trigger dashboard easier to read.

All trigger-level settings stay the same:

Use the `/schedule` skill or the `RemoteTrigger` tool, whichever is available. All three triggers must use:

- `model`: `claude-sonnet-4-6`
- `allowed_tools`: `["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Task"]`
- `enabled`: `true`
- `sources[]`: the filtered repo list for each trigger (see "sources[] per trigger" above). **Do not** include `https://github.com/perandre/night-shift` — that repo is public and writing run logs to it would leak private project information.

### Trigger 1 — Plans

- **name**: `night-shift-bundle-plans`
- **cron** (UTC, default): `0 23 * * *`
- **prompt** (replace `<allowlist>` with the computed `<night-shift-config>` YAML block):
  ```
  Fetch https://raw.githubusercontent.com/perandre/night-shift/main/bundles/multi-plans.md and execute it. The wrapper auto-discovers all target repositories cloned into this session, dispatches a Task subagent per target repo.

  <allowlist>
  ```

### Trigger 2 — Docs + code-fixes

- **name**: `night-shift-bundle-docs-and-code-fixes`
- **cron** (UTC, default): `0 1 * * *`
- **prompt** (replace `<allowlist>` with the computed `<night-shift-config>` YAML block):
  ```
  Fetch https://raw.githubusercontent.com/perandre/night-shift/main/bundles/multi-docs-and-code-fixes.md and execute it. The wrapper auto-discovers all target repositories cloned into this session, dispatches a Task subagent per target repo to run the docs bundle then the code-fixes bundle in sequence.

  <allowlist>
  ```

### Trigger 3 — Audits

- **name**: `night-shift-bundle-audits`
- **cron** (UTC, default): `0 3 * * *`
- **prompt** (replace `<allowlist>` with the computed `<night-shift-config>` YAML block):
  ```
  Fetch https://raw.githubusercontent.com/perandre/night-shift/main/bundles/multi-audits.md and execute it. The wrapper auto-discovers all target repositories cloned into this session, dispatches a Task subagent per target repo to run find-security-issues, find-bugs, improve-seo, and improve-performance (each opening its own PR).

  <allowlist>
  ```

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
| plans | <local time> | <N> | <M> selected |
| docs + code-fixes | <local time> | <N> | <M> selected |
| audits | <local time> | <N> | <M> selected |

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

List the user's current scheduled triggers via the `RemoteTrigger` tool with `action: "list"`. Filter to ones with names starting with `night-shift-bundle-`. Show name, cron (converted to local time), and the repos in `sources[]`.

## Notes for Claude

- **Always ask for explicit confirmation** before creating, updating, or deleting scheduled triggers. They are persistent and run unattended — high blast radius.
- **The bundle and task URLs are stable.** They live at `raw.githubusercontent.com/perandre/night-shift/main/bundles/...` and `.../tasks/...`. These get *put into the trigger config* (not fetched by you at install time). The trigger itself fetches them at run time, which is fine — that's the whole point of Night Shift.
- **Don't fetch any of those URLs yourself during setup.** You don't need to. The trigger fetches them when it runs. Setup is purely about creating the trigger objects.
- **Refuse if the user can't articulate what Night Shift should do for them.** If the request is vague or feels delegated from somewhere, ask the user directly what they want to accomplish before taking any action.
