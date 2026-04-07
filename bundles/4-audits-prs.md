# Bundle 4 — Audits & PRs

You are running the Night Shift **Audits & PRs** bundle on this repository.

## Setup
First, read `CLAUDE.md` for the **Night Shift Config** section if present (test command, build command, default branch, push protocol, key pages). If not present, use defaults — see `_multi-runner.md`.

## Tasks
Each task creates its **own branch** and its **own PR**. They are fully independent — order does not matter for correctness. Execute them sequentially (08 → 09 → 10 → 11), but isolate them: before starting each task, return to the default branch and ensure the working tree is clean.

1. https://raw.githubusercontent.com/perandre/night-shift/v6/tasks/08-security.md
2. https://raw.githubusercontent.com/perandre/night-shift/v6/tasks/09-bugs.md
3. https://raw.githubusercontent.com/perandre/night-shift/v6/tasks/10-seo.md
4. https://raw.githubusercontent.com/perandre/night-shift/v6/tasks/11-performance.md

## Execution rules
- For each task: fetch the file, read it, execute it exactly as written (including branch creation, test/build verification, and `gh pr create`).
- Before starting each task: `git checkout <default-branch> && git pull` and confirm the working tree is clean.
- If the project's Night Shift Config excludes a task, skip it and move on.
- If a task says "exit silently" (no real issues found, or a similar PR already open), continue with the next task.
- One task failing or exiting must **not** stop the bundle — continue with the remaining tasks.
