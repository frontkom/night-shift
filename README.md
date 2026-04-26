# Night Shift

![Night Shift](night-shift.png)

While you sleep, an AI agent works across your repositories. You wake up to fresh PRs and you decide what you want to keep. 

## Get started

**Install (run in your shell, not in Claude):**

```bash
npx skills add frontkom/night-shift
```


Or fetch the single file directly — no CLI required:

```bash
mkdir -p ~/.claude/skills/night-shift && \
  curl -fsSL https://raw.githubusercontent.com/frontkom/night-shift/main/skills/night-shift/SKILL.md \
  -o ~/.claude/skills/night-shift/SKILL.md
```

**Use:**

In any Claude Code session, type:

```
/night-shift
```

Claude will walk you through setup interactively — pick repos, choose tasks, confirm before anything is created.

Night Shift supports two backends:

| Backend | How it runs | Requirements |
|---|---|---|
| **Claude Routine** | Claude Code routines (runs on your account) | Claude subscription — no API key needed |
| **GitHub Actions** | GitHub-hosted runners via a reusable workflow | `ANTHROPIC_API_KEY` in org/repo secrets + `gh` CLI |

During setup, `/night-shift` runs a **per-repo task picker** — for each repo you add, you choose which of the tasks should run nightly. Defaults are all-on. To change a repo's selection later, re-run `/night-shift` and pick **Change tasks for a repo**.


## What you'll find in your repo tomorrow morning

- **Implemented plans** — picks the next phase from a `docs/*-PLAN.md` file and opens a PR
- **Updated docs** — changelog entries, user guide pages, decision records
- **New test coverage** — fills coverage gaps following your existing test patterns
- **Fixed accessibility issues** — WCAG AA violations on key pages
- **Translated UI strings** — moves hardcoded text into your i18n system
- **Audit PRs** — security, bug, SEO, and performance issues

Every Night Shift run leaves a labelled PR per task (`night-shift` + `night-shift:<bundle>`), so `gh pr list --label night-shift` is the audit trail — no per-repo log file is written.

## The bundles

| Bundle | What it does | Mode |
|---|---|---|
| **plans** | Implements the next phase of a planning document | One PR per plan |
| **docs** | Updates changelog, user guide, decision records, suggestions | One PR per task |
| **code-fixes** | Adds tests, fixes accessibility, completes translations | One PR per task |
| **audits** | Finds security / bug / SEO / performance issues | One PR per area |

`manifest.yml` is the single source of truth for what tasks exist, what they do, what bundle they belong to, and what order they run in. Edit one file to add, rename, reorder, or move tasks.

## GitHub Actions

To use the GitHub Actions backend, an org admin needs to add `ANTHROPIC_API_KEY` as an **organization secret**:

1. Go to your org's **Settings → Secrets and variables → Actions**
2. Click **New organization secret**
3. Name: `ANTHROPIC_API_KEY`, Value: your Anthropic API key
4. Repository access: select the repos Night Shift will manage (or "All repositories")

This is a one-time setup. Once the secret exists, any repo member can run `/night-shift`, choose **GitHub Actions**, and the skill will create PRs with the workflow file — no local clone needed.

You also need the [GitHub CLI](https://cli.github.com) (`gh`) installed and authenticated on your machine for the setup process.

## Stopping Night Shift on a project

Add **either**:
- An empty file `.nightshift-skip` at the repo root
- A line `Night Shift: skip` in `CLAUDE.md`, `AGENTS.md`, or `README.md`

The wrapper reports `opted-out` for that repo and moves on.

## Customising per project

Add a `## Night Shift Config` section to the project's `CLAUDE.md`. All fields are optional — anything unset uses sensible defaults autodetected from your `package.json` and repo layout.

```markdown
## Night Shift Config
- Doc language: Norwegian (nb)
- Test command: npm test
- Build command: npm run build
- Push: git push mirror main && git push origin main
- Key pages: /dashboard, /surveys, /people
```

## Recommended target-repo setup (optional)

These are hints, not requirements — your org may already have its own standards. 

**Enable a merge queue on `main`.** Night Shift opens several PRs in parallel at night. Without a queue, every PR sits on its original tree all day. As siblings land, each remaining PR goes stale — missing modules, merge conflicts, stale CI aggregators — and you spend your morning rebasing instead of reviewing. A merge queue rebases each PR onto fresh `main` and re-runs required checks at merge time, so freshness is guaranteed.

Suggested settings (GitHub → Settings → Rules → ruleset for `main`):
- Add a `merge_queue` rule: method `SQUASH`, grouping `ALLGREEN`.
- Keep required status checks; the queue re-runs them on the rebased commit.
- Allow merge method: squash only (keeps history linear).


**Selective human review for Night Shift PRs only.** If you don't want blanket "require 1 approval" on every human PR, but *do* want human approval before Night Shift PRs land, add a small workflow that gates on the `night-shift` label. Then mark `nightshift-review-gate` as a required status check. Human PRs skip it automatically; Night Shift PRs block on it until approved.

**Aggregator checks should treat `cancelled` as neutral, not failure.** If you use an aggregator job (one that waits on `needs:` and succeeds only if children pass — common for multi-app monorepos), make sure it only fails on `failure`. Otherwise, when concurrency cancels an older run (a common, desirable thing), the aggregator latches to red and the PR stays `BLOCKED` even though every real test passed. We got bitten by this three times in one night before fixing it.


## How to add a project, add a task, or run something now

See **[HOW-TO.md](HOW-TO.md)** — five copy-paste recipes covering the common operations.
