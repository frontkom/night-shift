# Bundle 1 — Plans

You are running the Night Shift **Plans** bundle on this repository.

## Setup
First, read `CLAUDE.md` for the **Night Shift Config** section if present (test command, build command, default branch). If not present, use defaults — see `_multi-runner.md`.

## Task
Run task 00 against this repository. It will pick **one** pending plan phase, implement it on a feature branch, verify with test + build, and open a PR.

1. https://raw.githubusercontent.com/perandre/night-shift/v6/tasks/00-implement-plans.md

## Execution rules
- Fetch the task file, read it, execute it exactly as written.
- One phase per night, ever — task 00 enforces this internally.
- If there are no pending phases, the task exits silently and that is success.
- Result is **one PR** per plan touched (or zero PRs if nothing pending).
- Never commit directly to the default branch in this bundle. All work goes through the PR flow in task 00.
