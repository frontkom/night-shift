# Plans bundle

You are running the Night Shift **Plans** bundle on this repository.

## Setup
Read `CLAUDE.md` for the **Night Shift Config** section if present. If absent, use defaults — see `_multi-runner.md`.

## Tasks
Run these tasks in order. See `manifest.yml` for full task metadata.

1. https://raw.githubusercontent.com/perandre/night-shift/v7/tasks/build-planned-features.md

## Rules
- Mode: **pull-request** — task creates a feature branch and opens a PR.
- One PR per plan, at most one phase implemented per night.
- If there are no pending plan phases, the task exits silently. That is success.
- Never commit directly to the default branch in this bundle.
