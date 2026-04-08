# Night Shift — How To

## For users

### Set up, add a project, check status
Type `/night-shift` in any Claude Code session. The skill walks you through it and asks before any scheduled-trigger change.

### Pause Night Shift on a project
In the project repo, do either of these:
- `touch .nightshift-skip` at the repo root
- Add a line `Night Shift: skip` to `CLAUDE.md`, `AGENTS.md`, or `README.md`

The next run reports `opted-out` and skips it. Remove the marker to re-enable.

### Run a bundle now without waiting
Open https://claude.ai/code/scheduled, click a trigger, click **Run now**. The summary table appears in the run output.

### Customise per project
Add a `## Night Shift Config` section to the project's `CLAUDE.md`. All fields optional — see the example in `README.md`. Without it, Night Shift autodetects sensible defaults.

## For framework maintainers

### Add a new task
1. Create `tasks/<task-id>.md` with the full task prompt. Copy any existing task file as a template.
2. Add an entry under `tasks:` in `manifest.yml`:
   ```yaml
   - id: check-outdated-deps
     title: Check for outdated dependencies
     description: Reports outdated packages and opens a PR.
     bundle: audits
     mode: pull-request
     order: 5
   ```
3. Commit and push to `main`. The bundle prompt resolves its task list from `manifest.yml` at runtime — **no bundle file edit needed**. Live on the next run.

### Rename or reorder a task
Edit `manifest.yml`. If the `id` changes, `git mv` the `tasks/<id>.md` file to match. Commit and push to `main`. Live on the next run.

### Add or rename a bundle
Edit the `bundles:` map in `manifest.yml`, then rename/create the matching `bundles/<id>.md` and `bundles/multi-<id>.md` files. Update the trigger prompt to point at the new `multi-*` URL.
