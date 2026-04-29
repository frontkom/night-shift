# Documentation

Discover and refresh all project documentation files — user guides, READMEs, technical docs, concept docs, model descriptions, ecosystem overviews, production-readiness checklists, and any other Markdown docs in the repo.

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: doc language, key pages, push protocol. If the dispatcher passed `allowed_tasks` and `update-user-guide` is not in it, exit silently.

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`):
- Look for docs both at `<app_path>/` and at the repo root.
- For user-facing docs (user manual, README), prefer per-app versions at `<app_path>/docs/` or `<app_path>/`. Create a per-app user manual at `<app_path>/docs/USER-MANUAL.md` if missing and the app has UI routes.
- For repo-wide docs (CONCEPT, TECH, MODELS, ECOSYSTEM, PRODUCTION-READINESS, ARCHITECTURE, etc.), update them in place — don't duplicate into app directories.
- Scope UI route walks to `<app_path>`. Read `key pages` from the scoped config.
- Commit message names the app when changes are app-scoped.

Without an `app_path`, behave as a single-app repo.

## Steps

### 1. Discover documentation files
Scan the repo root, `docs/` directory, and (when scoped) `<app_path>/` and `<app_path>/docs/` for Markdown files that are project documentation. This includes but is not limited to:

- **User-facing:** USER-MANUAL.md, README.md, GETTING-STARTED.md, CONTRIBUTING.md
- **Technical:** TECH.md, ARCHITECTURE.md, MODELS.md, API.md
- **Conceptual:** CONCEPT.md, GLOSSARY.md, ECOSYSTEM.md
- **Operational:** PRODUCTION-READINESS.md, DEPLOYMENT.md, RUNBOOK.md

Discover whatever exists — don't limit to this list.

**Exclude** files managed by other night-shift tasks or not meant for refresh:
- CHANGELOG.md, docs/CHANGELOG.md (managed by `update-changelog`)
- docs/adr/*.md (managed by `document-decisions`)
- docs/SUGGESTIONS.md (managed by `suggest-improvements`)
- CLAUDE.md, LICENSE*, .github/**, *-PLAN.md

### 2. Rank docs by staleness and pick ONE
For each discovered doc:

1. Read the file to understand what it documents.
2. Identify the source files it covers (routes, models, configs, components, etc.).
3. Compare the doc's last update (`git log -1 --format=%ci -- <doc-path>`) against changes in those source files (`git log --since=<doc-last-update> --oneline -- <relevant-paths>`).
4. If the source code hasn't changed, the doc is not stale — drop it from consideration.

After scoring, pick the **single stalest doc** (largest gap between its last update and the volume/significance of subsequent code changes). If nothing is clearly stale, exit silently.

### 3. Update the selected doc
For the one chosen doc:

1. Re-read the current source code the doc covers.
2. Update sections that are out of date: new features, renamed concepts, changed architecture, removed components, new dependencies, new routes.
3. Preserve the doc's existing structure, tone, and language. Do not rewrite sections that are still accurate.
4. Write in the configured **doc language**.
5. Do not touch any other doc file in this run — even if you notice other staleness. Future runs will pick them up.

For **user manuals** specifically, also walk UI routes and key components to document:
- What the user sees
- What actions are available
- What happens on each action (in user terms, not implementation terms)

**Do not create new doc files** except for the user manual (`USER-MANUAL.md`) when the app has UI routes and no manual exists yet.

## One doc file per run
Update **exactly one** doc file per run. Broad multi-file doc sweeps tend to get rejected as a unit because one bad section poisons the whole PR — lessons learned from past closed PRs. Pick the single stalest doc (largest gap between its last update and the changes in the code it covers) and update only that one. Leave the rest for subsequent runs; they will be picked up naturally on future nights.

If no single doc is clearly stale, exit silently.

## Branch, commit, and open the PR
This task runs in **pull-request mode** (per `manifest.yml`). Create a feature branch, commit your changes there, push, and open a PR with the standardized title format. Ensure labels exist (idempotent), then attach them. End the PR body with the Night Shift footer.

```
# Create the branch (include app slug when scoped):
# scoped:
git checkout -b night-shift/docs-<app-slug>-YYYY-MM-DD
# unscoped:
git checkout -b night-shift/docs-YYYY-MM-DD

git add -A
# scoped commit:
git commit -m "night-shift(docs): <app_path> — refresh <doc-filename>"
# unscoped commit:
git commit -m "night-shift(docs): refresh <doc-filename>"

git push -u origin HEAD

# Wrapper has already created the standard labels for this repo — just attach them.

cat > /tmp/night-shift-pr-body.md <<'EOF'
## Summary
- Refreshed <doc-filename> against current source code.

## Sections updated
- <bullet list of sections changed and why>

---
_Run by Night Shift • docs/update-user-guide_
EOF

# scoped PR title:
PR_URL=$(gh pr create --title "night-shift/docs: <app_path> — refresh <doc-filename>" \
  --label night-shift \
  --body-file /tmp/night-shift-pr-body.md)
# Post-create ritual — REQUIRED after every gh pr create. Do NOT return to the wrapper without running every line below. Skipping leaves PR bodies flattened (literal \n on GitHub) or auto-merge unarmed. Spec: bundles/_multi-runner.md.
gh pr edit "$PR_URL" --add-label night-shift
BODY=$(gh pr view "$PR_URL" --json body -q .body)
case "$BODY" in *'\n'*) printf '%s' "$BODY" | python3 -c "import sys;sys.stdout.write(sys.stdin.read().replace(chr(92)+chr(110),chr(10)))" > /tmp/night-shift-body-fix.md && gh pr edit "$PR_URL" --body-file /tmp/night-shift-body-fix.md ;; esac
gh pr merge "$PR_URL" --auto --squash 2>/dev/null || gh pr merge "$PR_URL" --auto || true
# unscoped PR title:
# PR_URL=$(gh pr create --title "night-shift/docs: refresh <doc-filename>" \
#   --label night-shift \
#   --body-file /tmp/night-shift-pr-body.md)
# gh pr edit "$PR_URL" --add-label night-shift
# BODY=$(gh pr view "$PR_URL" --json body -q .body)
# case "$BODY" in *'\n'*) printf '%s' "$BODY" | python3 -c "import sys;sys.stdout.write(sys.stdin.read().replace(chr(92)+chr(110),chr(10)))" > /tmp/night-shift-body-fix.md && gh pr edit "$PR_URL" --body-file /tmp/night-shift-body-fix.md ;; esac
# gh pr merge "$PR_URL" --auto --squash 2>/dev/null || gh pr merge "$PR_URL" --auto || true
```

**Always use `--body-file`, never inline `--body`.** See `bundles/_multi-runner.md` → "PR body formatting".

## Idempotency
- One doc file per run — even if multiple are stale, pick the stalest and leave the rest.
- Skip docs whose source code has not changed since the doc's last update.
- Never remove sections — only update or add content.
- If nothing is stale, exit silently.
