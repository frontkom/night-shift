# Docs bundle

You are running the Night Shift **Docs** bundle on this repository.

## Setup
Read `CLAUDE.md` for the **Night Shift Config** section if present. If absent, use defaults — see `_multi-runner.md`.

## Tasks
Run these tasks. They are independent and may run in any order. See `manifest.yml` for full task metadata.

1. https://raw.githubusercontent.com/perandre/night-shift/v7/tasks/update-changelog.md
2. https://raw.githubusercontent.com/perandre/night-shift/v7/tasks/update-user-guide.md
3. https://raw.githubusercontent.com/perandre/night-shift/v7/tasks/document-decisions.md
4. https://raw.githubusercontent.com/perandre/night-shift/v7/tasks/suggest-improvements.md

## Rules
- Mode: **direct-to-main** — each task commits straight to the default branch.
- Tasks are independent — one task's exit does not affect the others.
- If a task says "exit silently", that is success — continue with the rest.
