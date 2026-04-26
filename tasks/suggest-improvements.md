# Suggestions

Analyze the codebase for improvement ideas to pitch to the client. This is a **discovery** task — do not change code.

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: doc language, push protocol. If the dispatcher passed `allowed_tasks` and `suggest-improvements` is not in it, exit silently.

## High bar — default is silent
Only write a suggestion if you are confident it would clearly help the project. A mediocre suggestion wastes the client's reading time and dilutes the list. One strong suggestion beats three weak ones. **Zero new suggestions is a correct outcome on most nights** — do not pad to hit a number.

**Scoping.** This task is `scope: repo` in `manifest.yml`. Suggestions span the whole product, so even in a monorepo with `apps:` configured, this task runs **once per repo**, not once per app. Ignore any `app_path` passed by the multi-runner — the multi-docs-and-code-fixes wrapper will only dispatch this task during the first work-item of a repo.

## One mode per run — never mix housekeeping with net-new
Each run of this task does **exactly one** of the following, never both in the same PR:

- **Mode A — add new ideas:** propose up to 3 net-new suggestions and commit only those additions.
- **Mode B — update implementation status:** mark existing suggestions as implemented / obsolete based on current code, and commit only those status changes.

Pick the mode before writing anything. If you notice work that fits the other mode, leave it for the next run. Mixed PRs are hard to review and tend to get rejected as a unit — lessons learned from past closed PRs. The commit message and PR body must announce the mode so reviewers know what they're looking at.

## Steps
1. Open or create `docs/SUGGESTIONS.md` at the **repo root**.
2. Read existing suggestions carefully.
3. **Pick a mode.** Prefer **Mode B (status update)** when several existing suggestions look like they may already be implemented — stale suggestions are worse noise than a missing new one. Otherwise use **Mode A (new ideas)**.
4. **If Mode A — add new ideas:**
   - Look for opportunities across:
     - UX rough edges (confusing flows, missing feedback states, unclear errors)
     - Quick wins (small features that would clearly help users)
     - Tech-debt that is starting to hurt velocity
     - Missing observability / monitoring
     - Onboarding gaps for new users
   - For each suggestion, write:
     - **Title** (1 line)
     - **Why** (the user/business value, 2-3 sentences)
     - **Effort** (rough size: S / M / L)
     - **Files involved** (so a human can find their way in)
   - Cap at **3 new suggestions per night**. Do not touch the status of existing suggestions in this mode.
5. **If Mode B — update status:**
   - Walk existing suggestions and verify each against current code: is it implemented, partially implemented, or obsolete?
   - Mark implemented ones using the file's existing convention (e.g. `**Status: Implemented (YYYY-MM-DD)**`, a checkbox, or strikethrough — match what's already there).
   - Do not add, rewrite, or rephrase any suggestion text. Do not add new suggestions in this mode.
   - If no existing suggestion has changed status, exit silently.

## Branch, commit, and open the PR
This task runs in **pull-request mode** (per `manifest.yml`). Create a feature branch, commit your changes there, push, and open a PR with the standardized title format. Ensure labels exist (idempotent), then attach them. End the PR body with the Night Shift footer.

```
git checkout -b night-shift/suggestions-YYYY-MM-DD

git add docs/SUGGESTIONS.md
# Mode A commit:
git commit -m "night-shift(suggestions): add <N> ideas"
# Mode B commit:
# git commit -m "night-shift(suggestions): mark <N> implemented"

git push -u origin HEAD

# Wrapper has already created the standard labels for this repo — just attach them.

# Mode A body + PR:
cat > /tmp/night-shift-pr-body.md <<'EOF'
## Mode
A — added <N> new suggestions.

## New ideas
- <bullet per suggestion title>

---
_Run by Night Shift • docs/suggest-improvements_
EOF

PR_URL=$(gh pr create --title "night-shift/suggestions: add <N> ideas" \
  --label night-shift --label "night-shift:docs" \
  --body-file /tmp/night-shift-pr-body.md)
# Post-create ritual (spec: bundles/_multi-runner.md)
gh pr edit "$PR_URL" --add-label night-shift --add-label "night-shift:docs"
BODY=$(gh pr view "$PR_URL" --json body -q .body)
case "$BODY" in *'\n'*) printf '%s' "$BODY" | python3 -c "import sys;sys.stdout.write(sys.stdin.read().replace(chr(92)+chr(110),chr(10)))" > /tmp/night-shift-body-fix.md && gh pr edit "$PR_URL" --body-file /tmp/night-shift-body-fix.md ;; esac
gh pr merge "$PR_URL" --auto --squash 2>/dev/null || gh pr merge "$PR_URL" --auto || true

# Mode B body + PR:
# cat > /tmp/night-shift-pr-body.md <<'EOF'
# ## Mode
# B — status update only, no new suggestions added.
#
# ## Status changes
# - <bullet per item flipped, with new status>
#
# ---
# _Run by Night Shift • docs/suggest-improvements_
# EOF
#
# PR_URL=$(gh pr create --title "night-shift/suggestions: mark <N> implemented" \
#   --label night-shift --label "night-shift:docs" \
#   --body-file /tmp/night-shift-pr-body.md)
# gh pr edit "$PR_URL" --add-label night-shift --add-label "night-shift:docs"
# BODY=$(gh pr view "$PR_URL" --json body -q .body)
# case "$BODY" in *'\n'*) printf '%s' "$BODY" | python3 -c "import sys;sys.stdout.write(sys.stdin.read().replace(chr(92)+chr(110),chr(10)))" > /tmp/night-shift-body-fix.md && gh pr edit "$PR_URL" --body-file /tmp/night-shift-body-fix.md ;; esac
# gh pr merge "$PR_URL" --auto --squash 2>/dev/null || gh pr merge "$PR_URL" --auto || true
```

**Always use `--body-file`, never inline `--body`.** See `bundles/_multi-runner.md` → "PR body formatting".

## Idempotency
- Never duplicate an existing suggestion. If a topic is already listed, skip it.
- If nothing new comes to mind, exit silently. Do not pad.
