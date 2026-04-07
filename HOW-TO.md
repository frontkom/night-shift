# Night Shift — How To

Five recipes for the common operations. Each one is a single edit or click.

## 1. Add a new project

You want Night Shift to start running on a new repository.

1. Decide if you want to override any defaults. If yes, add a `## Night Shift Config` section to that project's `CLAUDE.md` (see the section "Customising per project" in `README.md`). If you're happy with defaults, skip this — Night Shift will autodetect test/build commands and run every applicable task.
2. Open https://claude.ai/code/scheduled and edit each Night Shift trigger you want this project included in. Add a new entry to the `sources[]` array:
   ```json
   {"git_repository": {"url": "https://github.com/your-org/your-new-repo"}}
   ```
3. That's it. The next scheduled run picks it up. The first morning you'll see `docs/NIGHTSHIFT-HISTORY.md` appear in the new repo with a one-line entry.

## 2. Add a new task

You want Night Shift to do something it doesn't currently do — say, "check for outdated dependencies".

1. Create `tasks/check-outdated-deps.md` describing what to do, how to verify, and how to commit. Use any existing task file as a template — they all follow the same structure.
2. Add an entry to `manifest.yml`:
   ```yaml
   - id: check-outdated-deps
     title: Check for outdated dependencies
     description: Reports outdated packages and opens a PR with the safest upgrades.
     bundle: audits           # or whichever bundle fits
     mode: pull-request       # or direct-to-main
     order: 5                 # last in its bundle
   ```
3. Add the task URL to the matching `bundles/<bundle>.md` file (one line).
4. Commit, tag a new version (`git tag v8 && git push origin v8`), and update the version in your scheduled trigger URLs.

## 3. Rename a task

You want `find-bugs` to be called `hunt-for-bugs` instead.

1. `git mv tasks/find-bugs.md tasks/hunt-for-bugs.md`
2. Update the `id:` and `title:` in `manifest.yml`.
3. Update the URL line in `bundles/audits.md`.
4. Commit, tag a new version, bump the trigger URLs.

(Renaming bundles works the same way: rename the file in `bundles/`, update `manifest.yml`, update the multi-* wrapper that calls it.)

## 4. Stop Night Shift on a project

You want Night Shift to leave a project alone, but you don't want to remove it from the trigger configuration.

In the project repo, do **either** of these:
- `touch .nightshift-skip` at the repo root
- Add a line `Night Shift: skip` anywhere in `CLAUDE.md`, `AGENTS.md`, or `README.md`

The next run will report `opted-out` for that project and skip it. Removing the marker re-enables it.

## 5. Run a bundle right now without waiting

You don't want to wait for the schedule.

1. Open https://claude.ai/code/scheduled.
2. Click the trigger you want to run.
3. Click **"Run now"**.

That's it. The summary table appears in the run output when it finishes — usually a few minutes per repo, longer if a plan implementation is involved.
