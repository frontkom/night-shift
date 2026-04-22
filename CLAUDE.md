# CLAUDE.md

## Workflow
- Commit and push after each change.
- Push protocol: `git push origin main`
- Always bump `NIGHT_SHIFT_VERSION` in `skills/night-shift/SKILL.md` when making changes to it. Increment the letter suffix (e.g. `2026-04-12a` → `2026-04-12b`), or use today's date with suffix `a` if the date changed. The version appears in **two places** that must stay in sync:
  1. The frontmatter `version:` field (line ~9)
  2. The HTML comment `<!-- NIGHT_SHIFT_VERSION: ... -->` (line ~14)
