# Work on Tagged Issues

Pick up GitHub Issues labeled `night-shift` and implement fixes/features as PRs. **One PR per issue, max 3 issues per run.**

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: test command, build command, default branch, push protocol. If the dispatcher passed `allowed_tasks` and `work-on-issues` is not in it, exit silently.

## Steps
1. Find tagged issues:
   ```
   gh issue list --label "night-shift" --state open --json number,title,body,labels,assignees
   ```
   If no issues are found, exit silently — this is expected. Not every repo will have tagged issues on any given night.

2. Process up to **3 issues** per run (oldest first). For each issue:

### Evaluate complexity
Read the issue body to understand what's needed. **Skip if too complex:** if the issue appears to require changes across more than ~5 files or involves major architectural changes, comment on the issue explaining why it was skipped and move to the next issue:
```
gh issue comment <number> --body "Night Shift reviewed this issue but skipped it — the scope appears to require changes across many files or involves architectural changes that need human guidance. Leaving for manual implementation."
```

### Check for existing PRs
Check for an existing open PR for this issue to avoid duplicates:
```
gh pr list --search "nightshift/issue in:title #<number>" --state open --json title
```
If a PR for the same issue is already open, skip silently.

### Create a branch
```
git checkout -b nightshift/issue-<number>-<short-slug>-YYYY-MM-DD
```
`<short-slug>` is a 3–5 word kebab-case summary of the issue title.

### Implement the fix/feature
- Read the issue body carefully and implement exactly what is described.
- Do not invent scope beyond what the issue asks for.
- Follow existing project conventions (code style, patterns, directory structure).

### Verify
Run the **test command** and **build command** from the project config. Both must pass.

If tests or build fail:
1. Revert all changes: `git checkout -- . && git clean -fd`
2. Return to the default branch: `git checkout <default-branch>`
3. Comment on the issue explaining what was tried and what failed:
   ```
   gh issue comment <number> --body "Night Shift attempted this issue but the implementation failed verification.

   **What was tried:** <brief description of the approach>

   **What failed:** <test/build output summary>

   Leaving for manual implementation."
   ```
4. Move on to the next issue.

### Open the PR
On success:
```
git add -A
git commit -m "nightshift(issue): #<number> — <short description>"
git push -u origin HEAD
gh pr create --title "nightshift/issue: #<number> — <short description>" \
  --body "$(cat <<'EOF'
Closes #<number>

## Issue
<issue title and link>

## Changes
- <bullets per file touched>

## Verification
- test command output: pass
- build command output: pass
EOF
)"
```

### Comment on the issue
After opening the PR, link it from the issue:
```
gh issue comment <number> --body "Night Shift opened a PR for this: #<pr-number>"
```

### Clean up between issues
Return to the default branch with a clean working tree before processing the next issue:
```
git checkout <default-branch>
```

## Rules
- **Never self-assign issues** — only work on issues explicitly tagged `night-shift` by a human.
- **Always open a PR, never push to main** — human review is mandatory for issue-driven work.
- **One PR per issue.** Do not bundle multiple issues into a single PR.
- **Max 3 issues per run.** If more than 3 are tagged, process the 3 oldest and leave the rest for the next night.

## Idempotency
- If no issues are labeled `night-shift`, exit silently.
- If a PR for the same issue is already open, skip that issue.
- If all issues are too complex or already have open PRs, exit silently.
