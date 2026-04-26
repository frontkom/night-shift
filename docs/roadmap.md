# Night Shift Roadmap

Night Shift today is a solid engine — it runs tasks and creates labelled PRs. The audit trail is the PR list itself (`gh pr list --label night-shift`). But for an org of 20+ developers and 50+ repos, the gaps are: visibility, measurability, and scope.

This roadmap closes those gaps in four phases.

## Phase 1: Slack notifications

**Goal:** Every developer sees what Night Shift did, without checking anything.

Add a Slack webhook step to the reusable GitHub Actions workflow. After Claude finishes, post a structured summary to a `#night-shift` channel.

Format:
```
Night Shift — repo-name — 2026-04-12

  plans:      ok — PR #142 (feature-x phase 3)
  docs:       ok — changelog + 1 ADR
  code-fixes: silent
  audits:     ok — PR #143 (XSS in /api/auth)

  3 PRs opened, 2 direct commits
```

**Why first:** Lowest effort, highest visibility. If nobody sees the output, nothing else matters. Also creates social proof — when one developer's repo gets improvements, others want it too, which drives adoption.

**Implementation:** One new step in the reusable workflow + a `SLACK_WEBHOOK_URL` secret.

## Phase 2: Central dashboard

**Goal:** One page showing all Night Shift activity across all repos.

Each Night Shift run posts a structured JSON event to a central location. A simple dashboard reads and displays it.

**Data model** (one event per run):
```json
{
  "repo": "frontkom/project-x",
  "timestamp": "2026-04-12T01:23:00Z",
  "bundles": {
    "plans": { "status": "ok", "prs": ["https://..."] },
    "docs": { "status": "ok", "commits": 2 },
    "code-fixes": { "status": "silent" },
    "audits": { "status": "ok", "prs": ["https://..."] }
  },
  "duration_seconds": 340,
  "model": "claude-opus-4-6",
  "backend": "github-actions"
}
```

**Storage options (pick one):**
- Append JSON to a file in a private `frontkom/night-shift-log` repo (simplest — git is the database)
- Neon/Supabase table via Vercel (richer querying, but more setup)

**Dashboard:** A simple Next.js app on Vercel that reads the log and shows:
- Last night's runs (all repos, one table)
- Per-repo history (drill down)
- Failures and repos that haven't run recently

## Phase 3: Metrics

**Goal:** Answer "is Night Shift worth it?" with numbers.

Once Phase 2 is collecting structured data, compute:

| Metric | What it measures |
|---|---|
| PRs opened per week | Volume of AI-generated work |
| PR merge rate | Quality signal — are developers accepting the work? |
| Time-to-merge | Are PRs being reviewed promptly or ignored? |
| Issues caught before production | Security findings, bugs found by audits |
| Repos active vs. total | Adoption rate across the org |
| Silent run rate | How often Night Shift finds nothing to do (diminishing returns signal) |

PR merge rate is the most important metric. If developers merge 80%+ of Night Shift PRs, it's high quality. Below 50%, the prompts need tuning.

**Implementation:** A weekly digest (Slack or email) with these numbers. Generated against the central event log from Phase 2 (or directly from `gh pr list --label night-shift` across the managed repos as a stopgap).

## Phase 4: Issue-driven work

**Goal:** Night Shift picks up real tasks, not just self-discovered maintenance.

Today Night Shift only does what its prompts define — it discovers work on its own. Phase 4 adds a new input: tagged issues.

**How it works:**
- Developers tag GitHub Issues with a `night-shift` label (or `ai-ok`, or a custom label per org)
- A new Night Shift task (`work-on-issues`) scans for these labels at the start of each run
- For each tagged issue, Night Shift reads the issue, implements the fix/feature on a branch, opens a PR, and links it back to the issue
- If the implementation isn't possible (too complex, unclear requirements), it comments on the issue explaining what it tried and what blocked it

**Why last:** This is the biggest behavioral change. Developers need to trust Night Shift's maintenance work (Phases 1-3) before they'll trust it with real feature work. The merge rate from Phase 3 is the trust signal.

**Scope guardrails:**
- Only issues tagged by a human — Night Shift never self-assigns
- Max complexity heuristic — skip issues with more than ~5 files of expected changes
- Always a PR, never direct to main — human review is mandatory for issue-driven work

## What this doesn't cover (intentionally)

- **Client-facing reports** — could be added later, but internal adoption comes first
- **Cost optimization** — model choice, turn limits, skipping idle repos — optimize after the system is proven valuable
- **Multi-model strategy** — using cheaper models for simpler tasks — premature optimization for now
