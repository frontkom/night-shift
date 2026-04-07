# Bundle 2 — Docs

You are running the Night Shift **Docs** bundle on this repository.

## Setup
First, read `CLAUDE.md` for the **Night Shift Config** section if present (doc language, push protocol, key pages). If not present, use defaults — see `_multi-runner.md`.

## Tasks
Tasks 01–04 are independent and can be done in any order.

1. https://raw.githubusercontent.com/perandre/night-shift/v6/tasks/01-changelog.md
2. https://raw.githubusercontent.com/perandre/night-shift/v6/tasks/02-user-manual.md
3. https://raw.githubusercontent.com/perandre/night-shift/v6/tasks/03-adr.md
4. https://raw.githubusercontent.com/perandre/night-shift/v6/tasks/04-suggestions.md

## Execution rules
- For each task: fetch the file, read it, execute it exactly as written (including its own commit and push steps).
- If the project's Night Shift Config excludes a task, skip it and move on.
- If a task says "exit silently", that is success — continue with the rest.
- Do **not** stop the bundle on a single task's exit. There's no verification dependency between docs tasks.
