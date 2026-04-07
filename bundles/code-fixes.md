# Code fixes bundle

You are running the Night Shift **Code fixes** bundle on this repository.

## Setup
Read `CLAUDE.md` for the **Night Shift Config** section if present. If absent, use defaults — see `_multi-runner.md`.

## Tasks
Run these tasks **strictly in order**. Each modifies code and must leave the test suite and build green before the next begins. See `manifest.yml` for full task metadata.

1. https://raw.githubusercontent.com/perandre/night-shift/v7/tasks/add-tests.md
2. https://raw.githubusercontent.com/perandre/night-shift/v7/tasks/improve-accessibility.md
3. https://raw.githubusercontent.com/perandre/night-shift/v7/tasks/translate-ui.md

## Rules
- Mode: **direct-to-main** — each task commits straight to the default branch.
- After each task commits, re-run the project's test and build commands to confirm a healthy baseline before starting the next.
- If a task says "exit silently", that is success — continue with the next task.
- If any task's verification step (test or build) **fails**, STOP the bundle immediately.
