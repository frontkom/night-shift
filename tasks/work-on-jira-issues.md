# Work on Tagged Jira Issues

Pick up Jira issues labelled `night-shift` in the repo's configured Jira project and implement them as GitHub PRs. **One PR per issue, max 3 issues per run.**

This task is the Jira-equivalent of `work-on-issues.md` (which handles GitHub Issues). The flow is identical except for issue discovery (Jira REST API instead of `gh issue list`), commenting back on the issue (Jira REST API instead of `gh issue comment`), and an extra best-effort step that transitions the Jira issue to "In Progress" once the PR is opened.

## Read project config first

Read `CLAUDE.md` for the **Night Shift Config** section: test command, build command, default branch, push protocol. Also read these Jira-specific keys:

- `Jira project key:` — e.g. `FGPW`. **Required.** If missing, exit silently — this repo has not opted in to a Jira project.
- `Jira label:` — optional, defaults to `night-shift`.

If the dispatcher passed `allowed_tasks` and `work-on-jira-issues` is not in it, exit silently.

## Read Jira credentials

Three environment variables are required:

- `JIRA_BASE_URL` — e.g. `https://frontkom.atlassian.net` (no trailing slash).
- `JIRA_EMAIL` — the Atlassian account email tied to the API token.
- `JIRA_API_TOKEN` — generate at id.atlassian.com → Security → API tokens.

If **any** of these are unset or empty, exit silently. Do not fail. Early adopters set the project key in `CLAUDE.md` before secrets are wired up; the task should stay quiet until the secrets land in the routine environment.

```
[ -n "$JIRA_BASE_URL" ] && [ -n "$JIRA_EMAIL" ] && [ -n "$JIRA_API_TOKEN" ] || { echo "silent | PRs: — | jira creds not set"; exit 0; }
```

## Steps

1. **List tagged Jira issues.** POST to `/rest/api/3/search/jql` (the GET `/rest/api/3/search` endpoint was deprecated May 2025) with a JQL query scoped to the project, label, and unfinished status. Note the request body is JSON; `fields` is a JSON array, not a comma-separated string:

   ```
   PROJECT_KEY="<from CLAUDE.md>"
   LABEL="${LABEL:-night-shift}"
   JQL="project = $PROJECT_KEY AND labels = \"$LABEL\" AND statusCategory != Done ORDER BY created ASC"

   REQ=$(jq -n --arg jql "$JQL" '{
     jql: $jql,
     fields: ["key","summary","description","status","priority","labels","assignee"],
     maxResults: 10
   }')

   curl -fsS -X POST -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
     -H "Content-Type: application/json" \
     -d "$REQ" \
     "$JIRA_BASE_URL/rest/api/3/search/jql"
   ```

   If the response has zero issues, exit silently — this is expected. Not every repo will have tagged Jira issues on any given night.

   On HTTP 4xx/5xx, exit silently with a `failed | PRs: — | jira API error: <code>` line. Do not retry — the routine runs again tomorrow.

2. Process up to **3 issues** per run (oldest first, by `created`). For each issue:

### Evaluate complexity

Read the issue's `summary` and `description` (the description is in Atlassian Document Format / ADF JSON — extract the text by walking the `content` tree, or just pass the JSON to your reasoning step; ADF is human-readable enough). **Skip if too complex:** if the issue requires changes across more than ~5 files or involves major architectural changes, comment on the issue explaining why and move to the next:

```
ISSUE_KEY="<from search response>"
COMMENT_BODY='{"body":{"type":"doc","version":1,"content":[{"type":"paragraph","content":[{"type":"text","text":"Night Shift reviewed this issue but skipped it — the scope appears to require changes across many files or involves architectural changes that need human guidance. Leaving for manual implementation."}]}]}}'

curl -fsS -X POST -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$COMMENT_BODY" \
  "$JIRA_BASE_URL/rest/api/3/issue/$ISSUE_KEY/comment" >/dev/null || true
```

### Check for existing PRs

Avoid duplicates by searching the GitHub repo for an existing open PR that names this Jira key:

```
gh pr list --search "night-shift/jira in:title $ISSUE_KEY" --state open --json title
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
1. Revert all changes: `git checkout -- . && git clean -fd`
2. Return to the default branch: `git checkout <default-branch>`
3. Comment on the Jira issue explaining what was tried and what failed:

   ```
   FAIL_TEXT="Night Shift attempted this issue but the implementation failed verification.\n\nWhat was tried: <approach>\n\nWhat failed: <test/build output summary>\n\nLeaving for manual implementation."
   FAIL_BODY=$(jq -n --arg t "$FAIL_TEXT" '{body:{type:"doc",version:1,content:[{type:"paragraph",content:[{type:"text",text:$t}]}]}}')
   curl -fsS -X POST -u "$JIRA_EMAIL:$JIRA_API_TOKEN" -H "Content-Type: application/json" -d "$FAIL_BODY" "$JIRA_BASE_URL/rest/api/3/issue/$ISSUE_KEY/comment" >/dev/null || true
   ```
4. Do **not** transition the issue. Move on to the next issue.

### Open the PR

On success. The wrapper has already created the standard labels for this repo — just attach them. End the body with the Night Shift footer:

```
git add -A
git commit -m "night-shift(jira): $ISSUE_KEY — <short description>"
git push -u origin HEAD

cat > /tmp/night-shift-pr-body.md <<'EOF'
## Plain summary
<1-2 sentences in English (PR review is always in English, regardless of the product's user language). What the user gets after this change merges — same level of clarity as the issue's own summary. No file paths or symbol names. See bundles/_multi-runner.md → "Body header — Plain summary".>

## Jira issue
- Key: <ISSUE_KEY>
- Summary: <issue summary>
- Link: <JIRA_BASE_URL>/browse/<ISSUE_KEY>

## Changes
- <bullets per file touched>

## Verification
- test command output: pass
- build command output: pass

---
_Run by Night Shift • plans/work-on-jira-issues_
EOF

PR_URL=$(gh pr create --title "night-shift/jira: $ISSUE_KEY — <short description>" \
  --label night-shift --label "night-shift:plans" \
  --body-file /tmp/night-shift-pr-body.md)
# Post-create ritual — REQUIRED after every gh pr create. Do NOT return to the wrapper without running every line below. Skipping leaves PR bodies flattened (literal \n on GitHub) or auto-merge unarmed. Spec: bundles/_multi-runner.md.
gh pr edit "$PR_URL" --add-label night-shift --add-label "night-shift:plans"
BODY=$(gh pr view "$PR_URL" --json body -q .body)
case "$BODY" in *'\n'*) printf '%s' "$BODY" | python3 -c "import sys;sys.stdout.write(sys.stdin.read().replace(chr(92)+chr(110),chr(10)))" > /tmp/night-shift-body-fix.md && gh pr edit "$PR_URL" --body-file /tmp/night-shift-body-fix.md ;; esac
gh pr merge "$PR_URL" --auto --squash 2>/dev/null || gh pr merge "$PR_URL" --auto || true
```

**Always use `--body-file`, never inline `--body`.** Inline body strings get silently flattened to one-liners with literal `\n` — the entire PR body then renders as one unbroken paragraph on GitHub. See `bundles/_multi-runner.md` → "PR body formatting".

**Self-review.** After the post-create ritual above, run the **Self-review + one revision** step from `_multi-runner.md` before continuing. One review, at most one revision commit, same branch; if the revision breaks tests, revert with `git push --force-with-lease` and keep the original PR.

### Comment on the Jira issue

Link the PR back from the issue:

```
LINK_TEXT="Night Shift opened a PR for this: $PR_URL"
LINK_BODY=$(jq -n --arg t "$LINK_TEXT" '{body:{type:"doc",version:1,content:[{type:"paragraph",content:[{type:"text",text:$t}]}]}}')
curl -fsS -X POST -u "$JIRA_EMAIL:$JIRA_API_TOKEN" -H "Content-Type: application/json" -d "$LINK_BODY" "$JIRA_BASE_URL/rest/api/3/issue/$ISSUE_KEY/comment" >/dev/null || true
```

### Transition the Jira issue to In Progress (best-effort)

After the comment lands, look up available transitions and pick one whose target status is in Jira's `indeterminate` (In Progress) status category. Some workflows already start issues in that category, others require a transition; some don't expose a clean transition at all. Swallow all errors — the PR is already open, the comment is already posted, the transition is purely cosmetic.

```
TRANSITIONS=$(curl -fsS -u "$JIRA_EMAIL:$JIRA_API_TOKEN" "$JIRA_BASE_URL/rest/api/3/issue/$ISSUE_KEY/transitions" || echo '{"transitions":[]}')
TRANSITION_ID=$(echo "$TRANSITIONS" | jq -r '.transitions[] | select(.to.statusCategory.key == "indeterminate") | .id' | head -1)
if [ -n "$TRANSITION_ID" ]; then
  curl -fsS -X POST -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"transition\":{\"id\":\"$TRANSITION_ID\"}}" \
    "$JIRA_BASE_URL/rest/api/3/issue/$ISSUE_KEY/transitions" >/dev/null || true
fi
```

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
- If any of `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` is unset, exit silently.
- If the JQL search returns zero issues, exit silently.
- If a GitHub PR for the same Jira key is already open, skip that issue.
- If all issues are too complex or already have open PRs, exit silently.
- The `gh pr list --search` query is the source of truth for "already worked on" — re-running on the same night is safe.

## Result line

Return one line to the dispatcher in this format:

```
<ok|silent|failed> | PRs: <comma-separated URLs or —> | <terse note, max 60 chars>
```

Examples:
- `ok | PRs: https://github.com/owner/repo/pull/42, https://github.com/owner/repo/pull/43 | 2 jira issues, 1 too complex`
- `silent | PRs: — | no jira issues labelled night-shift`
- `silent | PRs: — | jira creds not set`
- `failed | PRs: — | jira API error: 401`
