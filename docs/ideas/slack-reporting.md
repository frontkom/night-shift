# Idea: Slack reporting for Night Shift runs

Status: **not decided** — parked for later.

## The want

After a night's runs it's tedious to check 3 triggers × N repos in the Claude
Code dashboard. A push notification with a summary would close the loop.

Target channel (tentative): `#night-shift-notifications` in the Frontkom Slack
workspace.

## Shape

- **One digest per night**, posted at the end of the audits run (05:00 local).
- The audits wrapper reads each repo's `docs/NIGHTSHIFT-HISTORY.md` for the
  night's rows from all three bundles, composes a Block Kit message, and
  `curl`s it to a Slack incoming webhook.
- Message layout: one section per repo with inline PR links. For monorepos
  with `apps:` configured, `scope: app` rows are grouped under the app so
  reviewers can see at a glance which team owns each finding. `scope: repo`
  rows (ADRs, suggestions, secret scans) appear once at the repo level.
  ```
  🌙 Night Shift — 2026-04-09

  owner/repo-a
    ✓ plans: implemented 2 plans → #142
    ✓ docs: synced README → #143
    • audits: 1 security finding → #144

  owner/turbo-site
    apps/web
      ✓ plans: phase 3 implemented → #210
      ✓ audits: perf sweep → #211
    apps/admin
      • audits: 1 bug fix → #212
    (repo-wide)
      ✓ docs: 1 ADR added

  owner/repo-b
    — skipped (.nightshift-skip)
  ```
- Failure path: if the webhook call fails, dump the payload to the run's
  working dir (so it surfaces in the trigger dashboard) and continue. Never
  fail the whole run over a Slack hiccup.

## The open question

The webhook URL is a secret. "Hardcoded channel" + "public repo" don't mix.
Two viable paths:

### Option 1 — per-install env var (simplest)

- Wrapper in the public repo reads `$NIGHTSHIFT_SLACK_WEBHOOK` from the
  trigger env. Unset = silent skip.
- Per sets the var once on his own three triggers, out of band. Other people
  who install Night Shift post nothing by default.
- Skill setup flow stays untouched.
- Downside: doesn't achieve a *shared* channel across installations — only
  the owner's own runs post.

### Option 2 — relay endpoint

- A tiny Vercel function (owned by Per) whose URL is public but which holds
  the real Slack webhook server-side.
- Every Night Shift installation posts to the relay; relay forwards to
  Slack.
- Downside: adds infra to maintain. Abuse risk (anyone can hit the relay) —
  needs a shared secret or rate limit.

## Decision needed

- Is the goal "my own runs report to me" (→ Option 1) or "all Night Shift
  installations anywhere report into one shared channel" (→ Option 2)?
- Is one digest at 05:00 the right cadence, or one message per bundle?
- Channel per project, or everything in one channel?

## If we go with Option 1, concrete changes

- `bundles/multi-audits.md` — add a final "post digest" step gated on
  `$NIGHTSHIFT_SLACK_WEBHOOK`.
- `bundles/_multi-runner.md` (or similar) — helper block for the Block Kit
  payload, so all three wrappers could post individually later if we change
  our mind.
- `skill/SKILL.md` — untouched.
- Per sets `NIGHTSHIFT_SLACK_WEBHOOK` on his three triggers manually once.
