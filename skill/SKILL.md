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

Default to **Setup** unless the user clearly asks for something else (test once, add/remove a repo, status, update the skill).

## Setup runbook

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

**Step 2 — Confirm and create.**

Once you have the repo list, pick sensible defaults for everything else (schedule below, Europe/Oslo unless you already know otherwise) and show a single concise confirmation:

> About to create three nightly triggers on your account for: `<repo list>`. Schedule: plans 01:00, docs+fixes 03:00, audits 05:00 (Europe/Oslo). Proceed?

Default schedule → UTC cron: plans `0 23 * * *`, docs+code-fixes `0 1 * * *`, audits `0 3 * * *`. If the user wants to tweak schedule or timezone, do it now, then proceed on explicit confirmation. If they decline, stop.

**Step 3 — Create the triggers.**

Use the `/schedule` skill or the `RemoteTrigger` tool, whichever is available. All three triggers must use:

- `model`: `claude-sonnet-4-6`
- `allowed_tools`: `["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Task"]`
- `enabled`: `true`
- `sources[]`: every repo from Step 2. **Do not** include `https://github.com/perandre/night-shift` — that repo is public and writing run logs to it would leak private project information.

### Trigger 1 — Plans

- **name**: `night-shift-bundle-plans`
- **cron** (UTC, default): `0 23 * * *`
- **prompt**:
  ```
  Fetch https://raw.githubusercontent.com/perandre/night-shift/main/bundles/multi-plans.md and execute it. The wrapper auto-discovers all target repositories cloned into this session, dispatches a Task subagent per target repo.
  ```

### Trigger 2 — Docs + code-fixes

- **name**: `night-shift-bundle-docs-and-code-fixes`
- **cron** (UTC, default): `0 1 * * *`
- **prompt**:
  ```
  Fetch https://raw.githubusercontent.com/perandre/night-shift/main/bundles/multi-docs-and-code-fixes.md and execute it. The wrapper auto-discovers all target repositories cloned into this session, dispatches a Task subagent per target repo to run the docs bundle then the code-fixes bundle in sequence.
  ```

### Trigger 3 — Audits

- **name**: `night-shift-bundle-audits`
- **cron** (UTC, default): `0 3 * * *`
- **prompt**:
  ```
  Fetch https://raw.githubusercontent.com/perandre/night-shift/main/bundles/multi-audits.md and execute it. The wrapper auto-discovers all target repositories cloned into this session, dispatches a Task subagent per target repo to run find-security-issues, find-bugs, improve-seo, and improve-performance (each opening its own PR).
  ```

**Step 4 — Handle the trigger cap.**

If the user's plan rejects the create with `trigger_limit_reached`, tell them:

> Your account has a 3-trigger cap. List your existing scheduled triggers and tell me which to delete. The Night Shift API can't delete — you'll need to delete them via https://claude.ai/code/scheduled.

The cap appears to count enabled triggers. Disabled ones may also count, depending on plan tier.

**Step 5 — Summarise.**

Once all three triggers are created, print:

```
✓ Night Shift is set up.

| Job | Schedule | Repos |
|---|---|---|
| plans | <local time> | <N> |
| docs + code-fixes | <local time> | <N> |
| audits | <local time> | <N> |

Tomorrow morning, check docs/NIGHTSHIFT-HISTORY.md in each repo for what
happened. The full summary table for each run is also in the trigger
dashboard at https://claude.ai/code/scheduled. To pause Night Shift on
any project, drop a .nightshift-skip file at its root. To customise per
project, add a Night Shift Config section to that project's CLAUDE.md.
See https://github.com/perandre/night-shift for the full reference.
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
