# Night Shift

Centralized prompt library for scheduled Claude Code maintenance tasks across multiple projects.

Two layers of prompts a scheduled trigger can fetch and execute against any repo:

- **`tasks/`** — 12 atomic task prompts. Self-contained, one job each. Pick & choose per project.
- **`bundles/`** — 3 orchestration prompts that run multiple tasks in the right order with the right parallelism/sequencing rules. Designed for accounts with limited daily-trigger slots (e.g. 3 enabled triggers).

Project-specific details (test commands, key pages, doc language, push protocol) live in each project's `CLAUDE.md` under a **Night Shift Config** section — prompts here stay client-agnostic.

## Tasks

| # | Task | Mode |
|---|------|------|
| 00 | Implement plans | code, self-verified, direct to main |
| 01 | Changelog | docs, direct to main |
| 02 | User manual | docs, direct to main |
| 03 | ADR | docs, direct to main |
| 04 | Suggestions | docs, direct to main |
| 05 | Tests | code, self-verified, direct to main |
| 06 | Accessibility | code, self-verified, direct to main |
| 07 | i18n completeness | code, self-verified, direct to main |
| 08 | Security audit | one PR per issue |
| 09 | Bug hunt | one PR per issue |
| 10 | SEO & metadata | one big PR |
| 11 | Performance | one big PR |

Recommended execution order: `00 → 01-04 → 05 → 06 → 07 → 08 → 09 → 10 → 11`.

## Bundles

Three orchestration files in `bundles/` that run several tasks per scheduled session:

| Bundle | Tasks | Ordering |
|---|---|---|
| `1-plans-docs.md` | 00 → 01, 02, 03, 04 | 00 first; 01–04 independent |
| `2-code-verified.md` | 05 → 06 → 07 | strictly sequential, must keep tests green between |
| `3-audits-prs.md` | 08, 09, 10, 11 | independent; each opens its own PR |

Use bundles when your plan limits daily scheduled triggers — three bundles cover all 12 tasks in three slots.

## How triggers use it

In each project's scheduled trigger, use a thin wrapper prompt.

**Single task:**
```
Fetch https://raw.githubusercontent.com/perandre/night-shift/v2/tasks/05-tests.md
and execute it against this repository. Read CLAUDE.md for the Night Shift Config
section (test commands, build commands, key pages, push protocol, etc.).
```

**Bundle (recommended when trigger slots are limited):**
```
Fetch https://raw.githubusercontent.com/perandre/night-shift/v2/bundles/2-code-verified.md
and execute it against this repository. Read CLAUDE.md for the Night Shift Config
section.
```

The trigger contains no orchestration logic — all of it lives here.

## Per-project config

Add a **Night Shift Config** section to each project's `CLAUDE.md`. Recommended template:

```markdown
## Night Shift Config
- Tasks: 0, 1, 2, 4, 5, 6, 8, 9
- Doc language: Norwegian (nb)
- Test command: npm test
- Build command: npm run build
- Push: git push mirror main && git push origin main
- Key pages: /dashboard, /surveys, /people, /survey/demo
- Changelog format: "## Uke NN / ### Title / - Bullet"
```

Adjust the task list, push protocol, key pages, and language to match the project.

### Is config strictly required?

No — the bundles will still run without it, but behavior will be uneven:

**What breaks without config:**
- **Task subset filter** — every task in a bundle attempts to run. Tasks self-skip when there's nothing to do, so this is mostly noise, not damage.
- **Key pages** — a11y (06), SEO (10), perf (11) won't know which routes to focus on and will guess from the codebase.
- **Push protocol** — if you push to multiple remotes (e.g. `mirror` + `origin`), only `origin` gets the commits unless the config says otherwise.
- **Doc language** — changelog, user manual, ADR, suggestions will pick whatever the existing docs use, or default to English.
- **Changelog format** — task 01 will mimic existing entries; if there are none, it'll invent one.

**What still works without config:**
- Test/build commands — tasks autodetect from `package.json` (`npm test`, `pnpm test`, etc.).
- Git default branch — read from `git remote show origin`.

## Version pinning

Triggers reference a tagged version in the raw URL (`v2`, `v2`, ...).

- **Update all projects:** create a new tag, bump the version in each project's triggers.
- **Test changes:** point one project at a branch URL before tagging.
- **Roll back:** point triggers at the previous tag.

## Adding a new project

1. Add the **Night Shift Config** section to the project's `CLAUDE.md`.
2. Create scheduled triggers for the desired task subset, each fetching from `https://raw.githubusercontent.com/perandre/night-shift/v2/tasks/NN-*.md`.
3. Run each task once manually (daytime) to validate output quality.
4. Enable the schedule.
