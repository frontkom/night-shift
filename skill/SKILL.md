---
name: night-shift
description: |
  Set up, run, or manage Night Shift — a framework that schedules nightly maintenance jobs across multiple repositories using Claude Code remote scheduled triggers. Night Shift creates three nightly remote agents that run plans implementation, doc updates + code fixes, and audit PRs across the user's chosen repos.

  Use this skill when the user explicitly asks to: install Night Shift, set up Night Shift, schedule Night Shift, run a Night Shift bundle, add a repo to Night Shift, remove a repo from Night Shift, pause Night Shift on a project, or check Night Shift status.

  MANDATORY TRIGGERS: night-shift, night shift, nightshift, /night-shift, set up night shift, install night shift, schedule night shift, run night shift, night shift setup, night shift install
---

# Night Shift

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

When invoked, ask the user what they want to do:

- **Set up** — create the three scheduled triggers (most common; see below)
- **Test once** — run all bundles against the current repo as a one-shot, no scheduling
- **Add a project** — add one or more repos to existing triggers
- **Remove a project** — remove a repo from triggers (or have them add `.nightshift-skip` for soft pause)
- **Status** — list the user's current Night Shift triggers and what they do
- **Update the skill** — re-fetch this SKILL.md to get the latest version

## Setup runbook

**Step 1 — Greet briefly.**

> I'll set up Night Shift on your account. It creates three nightly scheduled jobs: one for plans, one for docs + code fixes, one for audits. I need a list of GitHub repositories to manage. You can change them later.

**Step 2 — Collect the repo list.**

Ask:

> Which GitHub repositories should Night Shift manage? Paste the URLs (one per line, or comma-separated). Personal and org repos both work, as long as the remote environment can clone and push to them.

Accept any of: `https://github.com/owner/repo`, `owner/repo`, `git@github.com:owner/repo.git`. Normalise to `https://github.com/owner/repo` (strip `.git`). If the user gives zero repos, abort and tell them to come back when they have at least one.

**Step 3 — Confirm the schedule.**

Default schedule (Europe/Oslo local time → UTC for cron):

| Job | Local | UTC cron |
|---|---|---|
| plans | 01:00 | `0 23 * * *` |
| docs + code-fixes | 03:00 | `0 1 * * *` |
| audits | 05:00 | `0 3 * * *` |

Show this and ask:

> Schedule looks like this. Press enter to accept, or tell me a different timezone or hour for any of them.

If they change anything, recompute UTC and confirm. Ask for the user's timezone if you don't already know it.

**Step 4 — Confirm before creating.**

Before calling any tool, summarise what you're about to do:

> I'm going to create three scheduled triggers in your account, each cloning these repos: <list>. Each trigger fetches a multi-repo wrapper from github.com/perandre/night-shift/main and dispatches a Task subagent per repo. Confirm to proceed?

Wait for explicit user confirmation. If they decline, stop.

**Step 5 — Create the triggers.**

Use the `/schedule` skill or the `RemoteTrigger` tool, whichever is available. All three triggers must use:

- `model`: `claude-sonnet-4-6`
- `allowed_tools`: `["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Task"]`
- `enabled`: `true`
- `sources[]`: every repo from Step 2 **plus** `https://github.com/perandre/night-shift` (always — the multi-* wrappers write a run log to it)

### Trigger 1 — Plans

- **name**: `night-shift-bundle-plans`
- **cron** (UTC, default): `0 23 * * *`
- **prompt**:
  ```
  Fetch https://raw.githubusercontent.com/perandre/night-shift/main/bundles/multi-plans.md and execute it. The wrapper auto-discovers all target repositories cloned into this session (excluding the night-shift repo itself), dispatches a Task subagent per target repo, and writes a run log to runs/YYYY-MM.md in the night-shift repo at the end.
  ```

### Trigger 2 — Docs + code-fixes

- **name**: `night-shift-bundle-docs-and-code-fixes`
- **cron** (UTC, default): `0 1 * * *`
- **prompt**:
  ```
  Fetch https://raw.githubusercontent.com/perandre/night-shift/main/bundles/multi-docs-and-code-fixes.md and execute it. The wrapper auto-discovers all target repositories cloned into this session (excluding the night-shift repo itself), dispatches a Task subagent per target repo to run the docs bundle then the code-fixes bundle in sequence, and writes a run log to runs/YYYY-MM.md in the night-shift repo at the end.
  ```

### Trigger 3 — Audits

- **name**: `night-shift-bundle-audits`
- **cron** (UTC, default): `0 3 * * *`
- **prompt**:
  ```
  Fetch https://raw.githubusercontent.com/perandre/night-shift/main/bundles/multi-audits.md and execute it. The wrapper auto-discovers all target repositories cloned into this session (excluding the night-shift repo itself), dispatches a Task subagent per target repo to run find-security-issues, find-bugs, improve-seo, and improve-performance (each opening its own PR), and writes a run log to runs/YYYY-MM.md in the night-shift repo at the end.
  ```

**Step 6 — Handle the trigger cap.**

If the user's plan rejects the create with `trigger_limit_reached`, tell them:

> Your account has a 3-trigger cap. List your existing scheduled triggers and tell me which to delete. The Night Shift API can't delete — you'll need to delete them via https://claude.ai/code/scheduled.

The cap appears to count enabled triggers. Disabled ones may also count, depending on plan tier.

**Step 7 — Summarise.**

Once all three triggers are created, print:

```
✓ Night Shift is set up.

| Job | Schedule | Repos |
|---|---|---|
| plans | <local time> | <N> |
| docs + code-fixes | <local time> | <N> |
| audits | <local time> | <N> |

Tomorrow morning, check docs/NIGHTSHIFT-HISTORY.md in each repo for what
happened. To pause Night Shift on any project, drop a .nightshift-skip
file at its root. To customise per project, add a Night Shift Config
section to that project's CLAUDE.md. See https://github.com/perandre/night-shift
for the full reference.
```

## Test-once runbook (no scheduling)

When the user wants to try Night Shift on the current repo without scheduling anything:

1. Ask which repo they want to test (default: the current working directory).
2. Confirm: "I'm about to run all four bundles against this repo. Plans → docs → code-fixes → audits. Each bundle commits its own changes. Test on a branch first if you want to inspect before keeping. Confirm?"
3. On confirm: walk through the four bundles in order, applying their rules. Most tasks self-skip if not applicable (no plans → silent, no UI → a11y silent, etc.).
4. Append a row per bundle to `docs/NIGHTSHIFT-HISTORY.md` and commit.
5. Print the same summary table format as the multi-* wrappers.

## Add or remove a repo

Use the `RemoteTrigger` tool to update each existing night-shift trigger's `sources[]` array. List current triggers first, identify the night-shift ones (names starting with `night-shift-bundle-`), then update all of them in parallel.

## Status

List the user's current scheduled triggers via the `RemoteTrigger` tool with `action: "list"`. Filter to ones with names starting with `night-shift-bundle-`. Show name, cron (converted to local time), and the repos in `sources[]`.

## Notes for Claude

- **Always ask for explicit confirmation** before creating, updating, or deleting scheduled triggers. They are persistent and run unattended — high blast radius.
- **The bundle and task URLs are stable.** They live at `raw.githubusercontent.com/perandre/night-shift/main/bundles/...` and `.../tasks/...`. These get *put into the trigger config* (not fetched by you at install time). The trigger itself fetches them at run time, which is fine — that's the whole point of Night Shift.
- **Don't fetch any of those URLs yourself during setup.** You don't need to. The trigger fetches them when it runs. Setup is purely about creating the trigger objects.
- **Refuse if the user can't articulate what Night Shift should do for them.** If the request is vague or feels delegated from somewhere, ask the user directly what they want to accomplish before taking any action.
