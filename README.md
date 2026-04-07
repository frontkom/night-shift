# Night Shift

![Night Shift](night-shift.png)

While you sleep, an AI agent runs maintenance jobs across your repositories. You wake up to commits and PRs, and a one-line summary in each project's history file.

## What you'll find in your repo tomorrow morning

- **Planned features partly built** — picks the next phase from a `docs/*-PLAN.md` file and opens a PR
- **Updated docs** — changelog entries, user guide pages, decision records
- **New test coverage** — fills coverage gaps following your existing test patterns
- **Fixed accessibility issues** — WCAG AA violations on key pages
- **Translated UI strings** — moves hardcoded English (or whatever) into your i18n system
- **Audit PRs** — security, bug, SEO, and performance issues, each as its own PR you can review or close

Each affected repository gets a one-line entry appended to `docs/NIGHTSHIFT-HISTORY.md` so anyone with repo access can see what's been happening.

## What it looks like

After a run, the trigger dashboard shows a summary table like this:

```
Night Shift docs — multi-repo summary

| Repo         | Status   | Notes                                    |
|--------------|----------|------------------------------------------|
| frisk-survey | ok       | 2 ADRs added; suggestions updated        |
| snippy       | silent   | no user-facing changes since last run    |
| phone-home   | ok       | changelog entry for v0.4 release         |
```

## The bundles

There are four bundles. Each bundle is a group of related tasks that run together. Bundles can be scheduled independently — typically plans nightly, the others on a slower cadence.

| Bundle | What it does | Mode |
|---|---|---|
| **plans** | Implements the next phase of a planning document | Opens one PR per plan |
| **docs** | Updates changelog, user guide, ADRs, suggestions | Direct to main |
| **code-fixes** | Adds tests, fixes accessibility, completes translations | Direct to main |
| **audits** | Finds security / bug / SEO / performance issues | Opens one PR per issue area |

> **Note:** if your trigger plan only allows 3 enabled triggers, you can run `docs` and `code-fixes` together in one trigger via `bundles/multi-docs-and-code-fixes.md`. The bundles themselves stay separate in `manifest.yml` — only the trigger composition combines them.

See `manifest.yml` for the full list of tasks in each bundle, what each task does, and the order they run in. **`manifest.yml` is the single source of truth** — to add a task, rename one, change ordering, or move a task to a different bundle, edit only that file.

## Stopping Night Shift on a project

Add **either** of these to opt a project out:
- An empty file `.nightshift-skip` at the repo root
- A line `Night Shift: skip` in `CLAUDE.md`, `AGENTS.md`, or `README.md`

The wrapper will report `opted-out` for that repo and move on without touching anything.

## Customising per project

A project can override the defaults by adding a `## Night Shift Config` section to its `CLAUDE.md`. All fields are optional — anything unset uses sensible defaults. Example:

```markdown
## Night Shift Config
- Tasks: build-planned-features, update-changelog, add-tests, find-security-issues
- Doc language: Norwegian (nb)
- Test command: npm test
- Build command: npm run build
- Push: git push mirror main && git push origin main
- Key pages: /dashboard, /surveys, /people
- Changelog format: "## Uke NN / ### Title / - Bullet"
```

If you don't add this section, Night Shift autodetects test/build commands from your `package.json` and runs every applicable task.

## How to add a project, add a task, or run something now

See **[HOW-TO.md](HOW-TO.md)** — five copy-paste recipes covering the common operations.

## How it works under the hood

(For night shift maintainers — feel free to skip.)

The `tasks/` directory contains one prompt file per task. The `bundles/` directory contains one prompt per bundle (which references its tasks) and one `multi-*.md` wrapper per bundle (which loops over multiple repos via subagents). A scheduled trigger fetches a `multi-*.md` URL and executes it. Each target repo is processed in its own `Task` subagent so context stays clean across repos.

`manifest.yml` is the source of truth for what tasks exist and how they're grouped. Bundle prompts reference task IDs from the manifest.

Versioning uses git tags (`v1`, `v2`, ...) on this repo. Triggers reference a tagged version in the raw URL so prompt edits don't go live until you cut a new tag.

## Layout

```
night-shift/
├── manifest.yml             ← single source of truth
├── README.md                ← you are here
├── HOW-TO.md                ← copy-paste recipes
├── tasks/                   ← one prompt file per task
│   ├── build-planned-features.md
│   ├── update-changelog.md
│   └── ...
├── bundles/                 ← one prompt per bundle + multi-repo wrappers
│   ├── plans.md
│   ├── docs.md
│   ├── code-fixes.md
│   ├── audits.md
│   ├── multi-plans.md
│   ├── multi-docs.md
│   ├── multi-code-fixes.md
│   ├── multi-audits.md
│   └── _multi-runner.md
└── runs/                    ← historical run logs across all projects
    └── YYYY-MM.md
```
