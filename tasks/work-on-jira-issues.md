# Work on Tagged Jira Issues

Pick up Jira issues labelled `night-shift` in the repo's configured Jira project and implement them as GitHub PRs. **One PR per issue, max 3 issues per run.**

This task is the Jira-equivalent of `work-on-issues.md` (which handles GitHub Issues). The flow is identical except for issue discovery, commenting back, and the optional best-effort transition to "In Progress".

## Tooling: Atlassian Rovo MCP connector

This task does **not** call Jira's REST API directly. Instead, it uses the **Atlassian Rovo** MCP connector that the routine has attached. From the connector's tool list, the task uses:

- **Search with JQL** — find issues by JQL (project + label + status filter).
- **Get issue** — read summary + description + status when needed.
- **Get transitions** — list available status transitions for an issue.
- **Transition issue** — move the issue to In Progress after the PR opens.
- **Update issue** (or whichever tool the connector exposes for adding a comment — try "Add comment" first, fall back to "Update issue" with a comment field) — comment back on the issue with the PR link.

If none of the Rovo MCP tools are callable in this session (connector not attached, OAuth lapsed, etc.), exit silently with `silent | PRs: — | rovo connector not available`. Do not fall back to Jira REST — the design choice is "Rovo connector or nothing", on purpose, because we don't want long-lived API tokens lying around.

## Read project config first

Read `CLAUDE.md` for the **Night Shift Config** section: test command, build command, default branch, push protocol. Also read these Jira-specific keys:

- `Jira project key:` — e.g. `FGPW`. **Required.** If missing, exit silently — this repo has not opted in to a Jira project.
- `Jira label:` — optional, defaults to `night-shift`.

If the dispatcher passed `allowed_tasks` and `work-on-jira-issues` is not in it, exit silently.

## Steps

1. **List tagged Jira issues.** Call the Rovo **Search with JQL** tool with this JQL (substitute `<KEY>` and `<LABEL>` from `CLAUDE.md`):

   ```
   project = <KEY> AND labels = "<LABEL>" AND statusCategory != Done ORDER BY created ASC
   ```

   Limit to the first 3 results. If zero issues come back, exit silently — this is expected. Not every repo will have tagged Jira issues every night.

2. For each of up to 3 issues (oldest first):

### Evaluate complexity

Read the issue's `summary` and `description`. **Skip if too complex:** if the fix requires changes across more than ~5 files or involves major architectural changes, comment on the issue explaining why, then move on:

> Body: `Night Shift reviewed this issue but skipped it — the scope appears to require changes across many files or involves architectural changes that need human guidance. Leaving for manual implementation.`

### Check for existing PRs

Avoid duplicates by searching the GitHub repo for an existing open PR that names this Jira key:

```
gh pr list --search "night-shift/jira in:title <ISSUE-KEY>" --state open --json title
```

If a PR for the same Jira key is already open, skip silently.

### Create a branch

```
git checkout -b night-shift/jira-<issue-key-lowercase>-<short-slug>-YYYY-MM-DD
```

`<short-slug>` is a 3–5 word kebab-case summary of the issue summary. Example: `night-shift/jira-fgpw-1234-fix-button-overlap-2026-04-28`.

### Implement the fix/feature

- Read the issue summary + description carefully and implement exactly what is described.
- Do not invent scope beyond what the issue asks for.
- Follow existing project conventions (code style, patterns, directory structure).

### Verify

Run the **test command** and **build command** from the project config. Both must pass.

If tests or build fail:
1. Revert: `git checkout -- . && git clean -fd`
2. Return to the default branch: `git checkout <default-branch>`
3. Comment on the Jira issue (via the Rovo comment tool) explaining what was tried and what failed:

   > `Night Shift attempted this issue but the implementation failed verification. What was tried: <approach>. What failed: <test/build summary>. Leaving for manual implementation.`
4. Do **not** transition the issue. Move on to the next issue.

### Open the PR

On success. The wrapper has already created the standard labels for this repo — just attach them. End the body with the Night Shift footer:

```
git add -A
git commit -m "night-shift(jira): <ISSUE_KEY> — <short description>"
git push -u origin HEAD

cat > /tmp/night-shift-pr-body.md <<'EOF'
## Plain summary
<1-2 sentences in English (PR review is always in English, regardless of the product's user language). What the user gets after this change merges — same level of clarity as the issue's own summary. No file paths or symbol names. See bundles/_multi-runner.md → "Body header — Plain summary".>

## Jira issue
- Key: <ISSUE_KEY>
- Summary: <issue summary>
- Link: <JIRA_BASE_URL>/browse/<ISSUE_KEY>   # JIRA_BASE_URL is the Atlassian site URL the Rovo tool returned

## Changes
- <bullets per file touched>

## Verification
- test command output: pass
- build command output: pass

---
_Run by Night Shift • plans/work-on-jira-issues_
EOF

PR_URL=$(gh pr create --title "night-shift/jira: <ISSUE_KEY> — <short description>" \
  --label night-shift \
  --body-file /tmp/night-shift-pr-body.md)
# Post-create ritual — REQUIRED after every gh pr create. Do NOT return to the wrapper without running every line below. Skipping leaves PR bodies flattened (literal \n on GitHub) or auto-merge unarmed. Spec: bundles/_multi-runner.md.
gh pr edit "$PR_URL" --add-label night-shift
BODY=$(gh pr view "$PR_URL" --json body -q .body)
case "$BODY" in *'\n'*) printf '%s' "$BODY" | python3 -c "import sys;sys.stdout.write(sys.stdin.read().replace(chr(92)+chr(110),chr(10)))" > /tmp/night-shift-body-fix.md && gh pr edit "$PR_URL" --body-file /tmp/night-shift-body-fix.md ;; esac
gh pr merge "$PR_URL" --auto --squash 2>/dev/null || gh pr merge "$PR_URL" --auto || true
```

**Always use `--body-file`, never inline `--body`.** Inline body strings get silently flattened to one-liners with literal `\n` — the entire PR body then renders as one unbroken paragraph on GitHub. See `bundles/_multi-runner.md` → "PR body formatting".

**Self-review.** After the post-create ritual above, run the **Self-review + one revision** step from `_multi-runner.md` before continuing. One review, at most one revision commit, same branch; if the revision breaks tests, revert with `git push --force-with-lease` and keep the original PR.

### Comment on the Jira issue

Call the Rovo comment tool to post the PR link back on the Jira issue. Body text:

> `Night Shift opened a PR for this: <PR_URL>`

If the connector exposes an explicit "Add comment" tool, use it. Otherwise use "Update issue" with a `comment.add` body field. If no comment tool is callable, log and continue — the PR is still open and labelled, so the work isn't lost.

### Transition the Jira issue to In Progress (best-effort)

After the comment lands, call **Get transitions** for the issue, find the first transition whose target status sits in Jira's `indeterminate` (In Progress) status category, and call **Transition issue** with that transition id. Some workflows already start issues in that category, others have non-standard transitions. Swallow all errors — the PR is already open, the comment is already posted, the transition is purely cosmetic.

### Clean up between issues

Return to the default branch with a clean working tree before processing the next issue:

```
git checkout <default-branch>
```

## Rules

- **Never self-assign issues** — only work on issues explicitly tagged `night-shift` by a human.
- **Always open a PR, never push to main** — human review is mandatory for issue-driven work.
- **One PR per Jira issue.** Do not bundle multiple Jira issues into a single PR.
- **Max 3 issues per run.** If more than 3 are tagged, process the 3 oldest and leave the rest for the next night.

## Idempotency

- If the repo's `CLAUDE.md` lacks `Jira project key:`, exit silently.
- If the Rovo MCP connector is not attached to this routine, exit silently.
- If the JQL search returns zero issues, exit silently.
- If a GitHub PR for the same Jira key is already open, skip that issue.
- If all issues are too complex or already have open PRs, exit silently.

## Result line

Return one line to the dispatcher in this format:

```
<ok|silent|failed> | PRs: <comma-separated URLs or —> | <terse note, max 60 chars>
```

Examples:
- `ok | PRs: https://github.com/owner/repo/pull/42, https://github.com/owner/repo/pull/43 | 2 jira issues, 1 too complex`
- `silent | PRs: — | no jira issues labelled night-shift`
- `silent | PRs: — | no Jira project key in CLAUDE.md`
- `silent | PRs: — | rovo connector not available`
