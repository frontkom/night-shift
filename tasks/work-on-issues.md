# Work on Tagged Issues

Pick up GitHub Issues labeled `night-shift` and implement fixes/features as PRs. **One PR per issue.**

This task runs in two modes:

- **Dispatched mode** (the multi-plans wrapper passed you a specific `ISSUE_NUMBER` in your prompt): work on that one issue only. Skip the discovery step. The wrapper has already discovered tagged issues and fanned out one subagent per issue.
- **Standalone mode** (no `ISSUE_NUMBER` in the prompt): discover all tagged issues yourself and process every one of them. There is no count cap — the multi-runner enforces the `Max PRs per morning` ceiling at the wrapper level.

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: test command, build command, default branch, push protocol. If the dispatcher passed `allowed_tasks` and `work-on-issues` is not in it, exit silently.

## Steps

**Dispatched mode:** if `ISSUE_NUMBER` was supplied, skip step 1 entirely and jump to step 2 with that single issue. The discovery line is the wrapper's responsibility.

1. **Standalone mode only.** Find tagged issues:
   ```
   gh issue list --label "night-shift" --state open --json number,title,body,labels,assignees
   ```
   If no issues are found, exit silently — this is expected. Not every repo will have tagged issues on any given night.

   **Print a discovery summary line** before doing any per-issue work, so the routines dashboard shows what was found vs. what was acted on. Format (one line, comma-separated, oldest first):
   ```
   Discovered tagged issues: #<n>, #<n>, ... (N total).
   ```
   If `N == 0`, print `Discovered tagged issues: none.` and exit silently. This mirrors the plans wrapper's `Discovered plans: ... (N total)` convention and is the single best signal that discovery itself is working.

2. Process every discovered issue (oldest first in standalone mode; the single supplied issue in dispatched mode). For each issue:

### Skip if the latest comment is already a Night Shift comment
**Before** running scope-evaluation or implementation, check whether the **most recent** comment on the issue starts with `Night Shift`. If it does, exit silently for this issue — the previous Night Shift run has already said what it needs to say, and there is no fresh human signal to react to.

```bash
LATEST_NS=$(gh issue view <number> --json comments \
  --jq '.comments | sort_by(.createdAt) | last | .body // "" | startswith("Night Shift")')
if [ "$LATEST_NS" = "true" ]; then
  # Last word on this issue is mine — silent skip. A human can override by
  # commenting / editing / removing comments.
  continue
fi
```

Why latest-comment instead of a date window: with one subagent per issue (the multi-plans wrapper's fan-out), parallel subagents would both pass a "no comment in last 7 days" check and double-post on the same fire. Latest-comment is atomic; the only way two subagents on the same issue conflict is if the wrapper dispatched two — which it doesn't (discovery returns each issue number exactly once).

A human who wants Night Shift to re-evaluate just adds any comment (asking a question, pointing at new info, or simply `please retry`) — that becomes the new latest comment and Night Shift will pick the issue up on the next run.

### Close if the work is already done
**Before** evaluating complexity or attempting an implementation, check whether the work described in the issue is **already in place** — the feature already exists in the codebase, the bug has been fixed in a prior PR, or the migration has already shipped. This is the most common "stuck open forever" failure mode: the issue was filed, someone fixed it in a side PR without linking it, and the issue lingers as backlog noise.

How to check: read the issue body, identify the specific symbol / file / behaviour it asks for, then look in the current `main` checkout for whether that thing exists. Examples of "already done" signals:

- The acceptance criterion ("function `foo` should accept `bar`") matches the current code.
- A recently-merged PR (`gh pr list --search "<keyword> is:merged" --state merged --limit 5`) describes the same work.
- The issue references a migration / endpoint / component that the codebase now contains.

If the work is already done, **close the issue as completed** with a comment linking to where the work lives:

```
gh issue close <number> --reason completed --comment "Night Shift reviewed this issue and the described work is already in place. <Specific pointer: file path, PR number, or commit SHA showing where it landed.> Closing as completed. Reopen if anything in the acceptance criteria is still missing."
```

Then move to the next issue. **Do not** open a PR. **Do not** post a freestanding comment that explains "this is already done" without also closing — leaving such a comment without the close is exactly what created the open-issue backlog this step exists to drain.

If you are not confident the work is fully done (only part of the acceptance criteria is in place, or you can't find a clean pointer), do **not** close. Fall through to "Evaluate complexity" and treat it like a normal issue.

### Evaluate scope
Read the issue body carefully and form a **concrete implementation plan**: which files to touch, which APIs to extend, which tests to add. Then implement it.

**Multi-file refactors and architectural changes are exactly what Night Shift is for.** Daytime is for small fixes; nights are for the deep work that needs hours of focused compute. A 30-file refactor, a cross-cutting type rewrite, a server-action security pass, splitting a 4,000-line monolith — all in scope. File count, line count, and architectural depth are **not** reasons to skip. The per-issue subagent has its own context window, so an ambitious refactor on this issue does not squeeze any sibling subagent's budget.

The only legitimate reasons to skip without opening a PR:
- The issue **needs a human business or product decision** that hasn't been made yet (e.g. "decide whether feature X should be a/b tested first", "pick between two competing API shapes").
- It **requires external access** Night Shift doesn't have (manual cloud DB migration, third-party vendor key, manual deploy, infra-team coordination).
- The issue body is **so vague** that you cannot form a concrete plan even after reading the referenced code and any linked context.

For those, leave a comment naming the specific blocker so the human can act, then move on:
```
gh issue comment <number> --body "Night Shift reviewed this issue but did not open a PR: <one-sentence specific reason — what decision is missing, what external access is needed, or what about the spec is too vague>. Add a comment with the missing information to retry on the next run."
```

If you can form a concrete plan, **just do it**. Do not punt to humans because "the scope is large" — that is exactly the work Night Shift was built to absorb.

### Check for existing PRs
Check for an existing open PR for this issue to avoid duplicates:
```
gh pr list --search "night-shift/issue in:title #<number>" --state open --json title
```
If a PR for the same issue is already open, skip silently.

### Create a branch
```
git checkout -b night-shift/issue-<number>-<short-slug>-YYYY-MM-DD
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
On success. The wrapper has already created the standard labels for this repo — just attach them. End the body with the Night Shift footer:
```
git add -A
git commit -m "night-shift(issue): #<number> — <short description>"
git push -u origin HEAD

cat > /tmp/night-shift-pr-body.md <<'EOF'
Closes #<number>

## Plain summary
<1-2 sentences in English (PR review is always in English, regardless of the product's user language). What the user gets after this change merges — same level of clarity as the issue's own description. No file paths or symbol names. See bundles/_multi-runner.md → "Body header — Plain summary".>

## Issue
<issue title and link>

## Changes
- <bullets per file touched>

## Verification
- test command output: pass
- build command output: pass

---
_Run by Night Shift • plans/work-on-issues_
EOF

# Stagger PR creation. Spec: bundles/_multi-runner.md → "PR creation throttle".
LAST=/tmp/night-shift-pr-last-created
if [ -f "$LAST" ]; then
  ELAPSED=$(( $(date +%s) - $(cat "$LAST") ))
  [ "$ELAPSED" -lt 90 ] && sleep "$((90 - ELAPSED))"
fi
PR_URL=$(gh pr create --title "night-shift/issue: #<number> — <short description>" \
  --label night-shift \
  --body-file /tmp/night-shift-pr-body.md)
date +%s > /tmp/night-shift-pr-last-created
# Post-create ritual — REQUIRED after every gh pr create. Do NOT return to the wrapper without running every line below. Skipping leaves PR bodies flattened (literal \n on GitHub) or auto-merge unarmed. Spec: bundles/_multi-runner.md.
gh pr edit "$PR_URL" --add-label night-shift
BODY=$(gh pr view "$PR_URL" --json body -q .body)
case "$BODY" in *'\n'*) printf '%s' "$BODY" | python3 -c "import sys;sys.stdout.write(sys.stdin.read().replace(chr(92)+chr(110),chr(10)))" > /tmp/night-shift-body-fix.md && gh pr edit "$PR_URL" --body-file /tmp/night-shift-body-fix.md ;; esac
gh pr merge "$PR_URL" --auto --squash 2>/dev/null || gh pr merge "$PR_URL" --auto || true
```

**Always use `--body-file`, never inline `--body`.** Inline body strings get silently flattened to one-liners with literal `\n` — the entire PR body then renders as one unbroken paragraph on GitHub. See `bundles/_multi-runner.md` → "PR body formatting".

**Self-review.** After the post-create ritual above, run the **Self-review + one revision** step from `_multi-runner.md` before returning your one-line result. One review, at most one revision commit, same branch; if the revision breaks tests, revert with `git push --force-with-lease` and keep the original PR.

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
- **No count cap.** When the wrapper dispatches you, it has already picked one issue for you. When you're running standalone, work every discovered tagged issue.

## Idempotency
- If no issues are labeled `night-shift`, exit silently.
- If a PR for the same issue is already open, skip that issue.
- If every discovered issue either has an open PR, was closed-as-completed by step 2, or hit a genuine blocker (missing decision / external access / vague spec), exit silently.
