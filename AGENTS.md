# AGENTS.md

## Workflow
- Commit and push after each change.
- Push protocol: `git push origin main && git push mirror main` (mirror = `perandre/ns`, hosts the GitHub Pages site at https://perandre.github.io/ns/)
- Always bump `NIGHT_SHIFT_VERSION` in `skills/night-shift/SKILL.md` on **any** framework-level change — not just edits to `SKILL.md` itself. That includes changes to `bundles/`, `tasks/`, `manifest.yml`, `reporting/`, `dashboard/`, `github-actions/`, or anything else under the repo root that a downstream user of the skill would want a refresh signal for. The version is the single fleet-wide "anything new?" marker; users only re-read the skill (and thus discover updated bundle behavior) when it bumps. Increment the letter suffix (e.g. `2026-04-12a` → `2026-04-12b`), or use today's date with suffix `a` if the date changed. The version appears in **two places** that must stay in sync:
  1. The frontmatter `version:` field (line ~9)
  2. The HTML comment `<!-- NIGHT_SHIFT_VERSION: ... -->` (line ~14)
