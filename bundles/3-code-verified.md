# Bundle 3 — Code Self-Verified

You are running the Night Shift **Code self-verified** bundle on this repository.

## Setup
First, read `CLAUDE.md` for the **Night Shift Config** section if present (test command, build command, push protocol, key pages). If not present, use defaults — see `_multi-runner.md`.

## Tasks
Run these tasks **strictly in order**. Each modifies code and must leave the test suite and build green before the next begins.

1. https://raw.githubusercontent.com/perandre/night-shift/v6/tasks/05-tests.md
2. https://raw.githubusercontent.com/perandre/night-shift/v6/tasks/06-accessibility.md
3. https://raw.githubusercontent.com/perandre/night-shift/v6/tasks/07-i18n.md

## Execution rules
- For each task: fetch the file, read it, execute it exactly as written.
- After each task commits, re-run the project's test command and build command to confirm the baseline is healthy before starting the next task.
- If the project's Night Shift Config excludes a task, skip it and move on.
- If a task says "exit silently", that is success — continue with the next task.
- If any task's verification step (test or build) **fails**, STOP the bundle immediately. Do not run subsequent tasks.
