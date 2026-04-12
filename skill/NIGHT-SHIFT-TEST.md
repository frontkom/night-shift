---
name: night-shift-test
description: |
  Quick end-to-end testing for Night Shift tasks against a sandbox repo.
  Run individual tasks, bundles, or the full pipeline and see real results (PRs, commits) instantly.
  
  MANDATORY TRIGGERS: /test night shift, night-shift-test, test night shift, /night-shift-test
version: 2026-04-12a
---

# Night Shift Test

Quick end-to-end testing for Night Shift tasks against a sandbox repo (`perandre/night-shift-sandbox`). Runs tasks locally — no triggers or GitHub Actions needed.

## Operations

Parse the user's input to determine the operation:

- `/night-shift-test <task-id>` — run one task (e.g., `find-bugs`, `update-docs`)
- `/night-shift-test <bundle-name>` — run one bundle (e.g., `audits`, `code-fixes`, `docs`, `plans`)
- `/night-shift-test all` — full pipeline (all 4 bundles in order)
- `/night-shift-test reset` — wipe sandbox back to seed state
- `/night-shift-test setup` — first-time setup (create repo, push seed)
- `/night-shift-test status` — show sandbox state (open PRs, branches, history)
- `/night-shift-test cleanup` — close all open PRs, delete nightshift/* branches, reset to main

## Setup (first-time or when sandbox doesn't exist)

Check if `perandre/night-shift-sandbox` exists:
```bash
gh repo view perandre/night-shift-sandbox --json name 2>/dev/null
```

If it doesn't exist:
1. Create it: `gh repo create perandre/night-shift-sandbox --public --description "Sandbox for testing Night Shift nightly maintenance tasks"`
2. Clone to `/tmp/night-shift-sandbox`
3. Copy seed files from the night-shift repo: `cp -r /Users/pesh/Sites/night-shift/tests/sandbox-seed/* /tmp/night-shift-sandbox/`
4. Also copy hidden files like .gitignore if present: `cp /Users/pesh/Sites/night-shift/tests/sandbox-seed/.* /tmp/night-shift-sandbox/ 2>/dev/null || true`
5. Commit and push the seed content
6. Create a GitHub issue labeled "night-shift" for testing work-on-issues:
   ```bash
   gh issue create --repo perandre/night-shift-sandbox \
     --title "Add search results count display" \
     --body "When search returns results, show a count like '12 results found' above the list. Should handle zero results with a friendly message." \
     --label "night-shift"
   ```
7. Report setup complete

If the sandbox repo doesn't exist when the user requests any other operation, run setup automatically first.

## Reset operation

1. Clone fresh or use existing `/tmp/night-shift-sandbox`
2. Close all open PRs:
   ```bash
   gh pr list --repo perandre/night-shift-sandbox --state open --json number -q '.[].number' | xargs -I{} gh pr close {} --repo perandre/night-shift-sandbox
   ```
3. Delete all remote nightshift/* branches:
   ```bash
   git ls-remote --heads origin 'nightshift/*' | awk '{print $2}' | sed 's|refs/heads/||' | xargs -I{} git push origin --delete {}
   ```
4. Reset main to seed state:
   - `git checkout main`
   - `git rm -rf .` (remove everything)
   - Copy seed files back from `/Users/pesh/Sites/night-shift/tests/sandbox-seed/`
   - Also copy hidden files: `cp /Users/pesh/Sites/night-shift/tests/sandbox-seed/.* /tmp/night-shift-sandbox/ 2>/dev/null || true`
   - `git add -A && git commit -m "Reset sandbox to seed state" && git push origin main --force`
5. Re-create the test issue if needed:
   ```bash
   gh issue list --repo perandre/night-shift-sandbox --label "night-shift" --state open --json number -q 'length'
   ```
   If 0, create the issue again (same as setup step 6).
6. Report reset complete

## Running a task

When the user specifies a task id (e.g., `find-bugs`):

1. **Validate** the task id exists in `/Users/pesh/Sites/night-shift/manifest.yml`
2. **Prepare workspace**:
   - If `/tmp/night-shift-sandbox` doesn't exist or isn't a git repo, clone: `git clone https://github.com/perandre/night-shift-sandbox /tmp/night-shift-sandbox`
   - `cd /tmp/night-shift-sandbox && git checkout main && git pull`
3. **Read the task prompt** from the LOCAL night-shift repo: `/Users/pesh/Sites/night-shift/tasks/<task-id>.md`
4. **Execute** the task against `/tmp/night-shift-sandbox` by following the task prompt instructions. The working directory is `/tmp/night-shift-sandbox`. Read CLAUDE.md there for config.
5. **Report results**:
   - PRs opened (with links)
   - Commits made
   - NIGHTSHIFT-HISTORY.md entries added
   - Any branches created

IMPORTANT: Read task prompts from the LOCAL repo (`/Users/pesh/Sites/night-shift/tasks/`), NOT from GitHub. This lets the user edit a task prompt and immediately re-test without committing.

## Running a bundle

When the user specifies a bundle name (plans, docs, code-fixes, audits):

1. **Read manifest.yml** from `/Users/pesh/Sites/night-shift/manifest.yml` and find all tasks where `bundle: <name>`, sorted by `order`
2. **Apply bundle rules** from the manifest (parallelism, stop_on_failure)
3. **Run each task** in order using the "Running a task" flow above
4. **Return to main** with clean working tree between tasks: `cd /tmp/night-shift-sandbox && git checkout main && git pull`
5. **Report combined results** — one summary table

## Running all

Run all four bundles in order: plans -> docs -> code-fixes -> audits. Return to main between bundles.

## Status operation

Show current sandbox state:
```
Sandbox: perandre/night-shift-sandbox

Open PRs:
  - #3 nightshift/a11y: Improve accessibility (opened 2h ago)
  - #2 nightshift/tests: Add missing tests (opened 2h ago)

Branches:
  - nightshift/a11y-2026-04-12
  - nightshift/tests-2026-04-12

Recent history (docs/NIGHTSHIFT-HISTORY.md):
  - 2026-04-12 code-fixes — ok Added 5 tests
  - 2026-04-12 audits — ok 1; Found XSS in contact form

Night-shift labeled issues:
  - #1 Add search results count display (open)
```

Gather this by running:
```bash
# Open PRs
gh pr list --repo perandre/night-shift-sandbox --state open --json number,title,headRefName,createdAt

# Remote nightshift branches
git ls-remote --heads origin 'nightshift/*'

# History file
cat /tmp/night-shift-sandbox/docs/NIGHTSHIFT-HISTORY.md 2>/dev/null || echo "No history file yet"

# Night-shift labeled issues
gh issue list --repo perandre/night-shift-sandbox --label "night-shift" --json number,title,state
```

## Cleanup operation

Close all open PRs and delete all nightshift/* branches, but DON'T reset the code. Useful for cleaning up after a test run while keeping the current code state.

```bash
# Close all open PRs
gh pr list --repo perandre/night-shift-sandbox --state open --json number -q '.[].number' | xargs -I{} gh pr close {} --repo perandre/night-shift-sandbox

# Delete all remote nightshift/* branches
cd /tmp/night-shift-sandbox && git ls-remote --heads origin 'nightshift/*' | awk '{print $2}' | sed 's|refs/heads/||' | xargs -I{} git push origin --delete {}
```

## Important notes

- Always `cd /tmp/night-shift-sandbox` before executing task prompts
- Read task .md files from LOCAL `/Users/pesh/Sites/night-shift/tasks/` (not GitHub)
- Read bundle .md files from LOCAL `/Users/pesh/Sites/night-shift/bundles/` (not GitHub)
- After running a task, always return to main: `git checkout main`
- The sandbox is disposable — reset liberally if things get messy
- If the sandbox repo doesn't exist yet, run setup automatically before the requested operation
- Show a brief summary after each operation, not a wall of text
