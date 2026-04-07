# Night Shift

![Night Shift](night-shift.png)

While you sleep, an AI agent runs maintenance jobs across your repositories. You wake up to commits and PRs, and a one-line summary in each project's history file.

## Get started

Night Shift installs as a Claude Code skill — a local file in `~/.claude/skills/`. Once installed, type `/night-shift` in any project to set up, run, or manage it.

**Install (run in your shell, not in Claude):**

```bash
mkdir -p ~/.claude/skills/night-shift && \
  curl -fsSL https://raw.githubusercontent.com/perandre/night-shift/main/skill/SKILL.md \
  -o ~/.claude/skills/night-shift/SKILL.md
```

That fetches one file into your local skills directory. No code execution, no Claude trust required — you can read the file before or after with `cat ~/.claude/skills/night-shift/SKILL.md`.

**Use:**

In any Claude Code session, type:

```
/night-shift
```

Claude will ask what you want to do (set up, test once, add a repo, status), walk you through it interactively, and confirm with you before creating any scheduled triggers.

**Why a skill instead of a paste-able prompt?**

Skills are loaded from your local trusted directory, not fetched at runtime. That means Claude has full context about what Night Shift is and what setup means *before* you ask for anything. A blind "fetch this URL and follow it" prompt would (correctly) be refused as a prompt-injection vector by any well-aligned Claude. A locally-installed skill carries the same information without the trust problem.

**Update later:**

Re-run the install command above. It overwrites the file with the latest version.

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

## Stopping Night Shift on a project

Add **either**:
- An empty file `.nightshift-skip` at the repo root
- A line `Night Shift: skip` in `CLAUDE.md`, `AGENTS.md`, or `README.md`

The wrapper reports `opted-out` for that repo and moves on.

## Customising per project

Add a `## Night Shift Config` section to the project's `CLAUDE.md`. All fields are optional — anything unset uses sensible defaults autodetected from your `package.json` and repo layout.

```markdown
## Night Shift Config
- Tasks: build-planned-features, update-changelog, add-tests, find-security-issues
- Doc language: Norwegian (nb)
- Test command: npm test
- Build command: npm run build
- Push: git push mirror main && git push origin main
- Key pages: /dashboard, /surveys, /people
```

## How to add a project, add a task, or run something now

See **[HOW-TO.md](HOW-TO.md)** — five copy-paste recipes covering the common operations.
