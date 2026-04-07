# Audits bundle

You are running the Night Shift **Audits** bundle on this repository.

## Setup
Read `CLAUDE.md` for the **Night Shift Config** section if present. If absent, use defaults — see `_multi-runner.md`.

## Tasks
Each task creates its own branch and its own PR. Run them sequentially but isolated: return to the default branch and ensure the working tree is clean before starting each one. See `manifest.yml` for full task metadata.

1. https://raw.githubusercontent.com/perandre/night-shift/v7/tasks/find-security-issues.md
2. https://raw.githubusercontent.com/perandre/night-shift/v7/tasks/find-bugs.md
3. https://raw.githubusercontent.com/perandre/night-shift/v7/tasks/improve-seo.md
4. https://raw.githubusercontent.com/perandre/night-shift/v7/tasks/improve-performance.md

## Rules
- Mode: **pull-request** — each task creates a feature branch and opens a PR.
- Tasks are independent — one task failing must not stop the bundle.
- If a task says "exit silently" (no real issues found, or a similar PR already open), continue with the next.
