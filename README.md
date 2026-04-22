# Night Shift

![Night Shift](night-shift.png)

While you sleep, an AI agent runs maintenance jobs across your repositories. You wake up to commits and PRs, and a one-line summary in each project's history file.

## Get started

Night Shift installs as a Claude Code skill — a local file in `~/.claude/skills/`. Once installed, type `/night-shift` in any project to set up, run, or manage it.

**Install (run in your shell, not in Claude):**

```bash
mkdir -p ~/.claude/skills/night-shift && \
  curl -fsSL https://raw.githubusercontent.com/frontkom/night-shift/main/skill/SKILL.md \
  -o ~/.claude/skills/night-shift/SKILL.md
```

That fetches one file into your local skills directory. No code execution, no Claude trust required — you can read the file before or after with `cat ~/.claude/skills/night-shift/SKILL.md`.

**Use:**

In any Claude Code session, type:

```
/night-shift
```

Claude will walk you through setup interactively — pick repos, choose tasks, confirm before anything is created.

Night Shift supports two backends:

| Backend | How it runs | Requirements |
|---|---|---|
| **Schedule** | Claude Code routines (runs on your account) | Claude subscription — no API key needed |
| **GitHub Actions** | GitHub-hosted runners via a reusable workflow | `ANTHROPIC_API_KEY` in org/repo secrets + `gh` CLI |

During setup, `/night-shift` runs a **per-repo task picker** — for each repo you add, you choose which of the 12 tasks should run nightly. Defaults are all-on, with a warning that the 4 audit tasks open PRs when they find issues. To change a repo's selection later, re-run `/night-shift` and pick **Change tasks for a repo**.


## What you'll find in your repo tomorrow morning

- **Planned features partly built** — picks the next phase from a `docs/*-PLAN.md` file and opens a PR
- **Updated docs** — changelog entries, user guide pages, decision records
- **New test coverage** — fills coverage gaps following your existing test patterns
- **Fixed accessibility issues** — WCAG AA violations on key pages
- **Translated UI strings** — moves hardcoded text into your i18n system
- **Audit PRs** — security, bug, SEO, and performance issues, each as its own PR

Each affected repo gets a one-line entry in `docs/NIGHTSHIFT-HISTORY.md`.

## The bundles

| Bundle | What it does | Mode |
|---|---|---|
| **plans** | Implements the next phase of a planning document | One PR per plan |
| **docs** | Updates changelog, user guide, decision records, suggestions | Direct to main |
| **code-fixes** | Adds tests, fixes accessibility, completes translations | Direct to main |
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

**Task selection is not in this file.** Which tasks run on which repo is decided at setup time via the picker in `/night-shift`, and stored in the routine prompts themselves. To change a repo's task selection, re-run `/night-shift` and pick **Change tasks for a repo**.

## Recommended target-repo setup (optional)

These are hints, not requirements — your org may already have its own standards. They come from running Night Shift against a real monorepo and hitting the same merge-time issues more than once. Adopt whatever fits.

**Enable a merge queue on `main`.** Night Shift opens several PRs in parallel at night. Without a queue, every PR sits on its original tree all day. As siblings land, each remaining PR goes stale — missing modules, merge conflicts, stale CI aggregators — and you spend your morning rebasing instead of reviewing. A merge queue rebases each PR onto fresh `main` and re-runs required checks at merge time, so freshness is guaranteed.

Suggested settings (GitHub → Settings → Rules → ruleset for `main`):
- Add a `merge_queue` rule: method `SQUASH`, grouping `ALLGREEN`.
- Keep required status checks; the queue re-runs them on the rebased commit.
- Allow merge method: squash only (keeps history linear).

**Arm auto-merge on every Night Shift PR.** Night Shift already does this: every `gh pr create` is followed by `gh pr merge --auto --squash`. The PR waits for required checks and review, then enters the queue the moment you approve in the morning. Nothing to configure per-repo — it's built into the PR creation pattern.

**Selective human review for Night Shift PRs only.** If you don't want blanket "require 1 approval" on every human PR, but *do* want human approval before Night Shift PRs land, add a small workflow that gates on the `night-shift` label:

```yaml
# .github/workflows/nightshift-review-gate.yml
name: Night Shift review gate
on:
  pull_request:
    types: [opened, reopened, synchronize, labeled, unlabeled]
  pull_request_review:
    types: [submitted, dismissed]
jobs:
  nightshift-review-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/github-script@v7
        with:
          script: |
            const pr = context.payload.pull_request;
            const labels = (pr.labels || []).map(l => l.name);
            if (!labels.includes('night-shift')) return;
            const reviews = await github.paginate(github.rest.pulls.listReviews, {
              owner: context.repo.owner, repo: context.repo.repo,
              pull_number: pr.number, per_page: 100,
            });
            const latest = new Map();
            for (const r of reviews) {
              if (r.state === 'COMMENTED') continue;
              latest.set(r.user.login, r.state);
            }
            const approvals = [...latest.values()].filter(s => s === 'APPROVED').length;
            if (approvals < 1) core.setFailed(`Night Shift PR requires 1 approval (has ${approvals}).`);
```

Then mark `nightshift-review-gate` as a required status check. Human PRs skip it automatically; Night Shift PRs block on it until approved.

**Aggregator checks should treat `cancelled` as neutral, not failure.** If you use an aggregator job (one that waits on `needs:` and succeeds only if children pass — common for multi-app monorepos), make sure it only fails on `failure`:

```yaml
- run: |
    # Only 'failure' fails the aggregator. 'cancelled' means superseded,
    # 'skipped' means not applicable — both should pass.
    if [ "${{ needs.some-job.result }}" = "failure" ]; then exit 1; fi
```

Otherwise, when concurrency cancels an older run (a common, desirable thing), the aggregator latches to red and the PR stays `BLOCKED` even though every real test passed. We got bitten by this three times in one night before fixing it.

**That's the whole recipe.** With those four pieces in place — merge queue, auto-merge armed by Night Shift, a selective review gate, and a `cancelled`-neutral aggregator — the nightly run lands cleanly the morning after, with no branch babysitting.

## Testing

To test tasks against a sandbox repo before running them on real projects, install the separate [Night Shift Test](https://github.com/perandre/night-shift-test) skill.

## How to add a project, add a task, or run something now

See **[HOW-TO.md](HOW-TO.md)** — five copy-paste recipes covering the common operations.
