# Changelog

Update the project's changelog if there are new user-facing changes since the last entry.

## Read project config first
Read `CLAUDE.md` for the **Night Shift Config** section: doc language, changelog format, push protocol. If the dispatcher passed `allowed_tasks` and `update-changelog` is not in it, exit silently.

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`):
- Prefer a per-app changelog at `<app_path>/CHANGELOG.md`. Create it if missing.
- If the app has no changelog but the repo root does (`CHANGELOG.md` or `docs/CHANGELOG.md`), write to the repo-root changelog **and** prefix each entry with the app name so readers know which app changed (`- (web) Added …`).
- Scope the `git log` to paths under `<app_path>`:
  `git log --since=<last-entry-date> --no-merges --oneline -- <app_path>`
- Commit message names the app: `nightshift(changelog): <app_path> — update for recent user-facing changes`.

Without an `app_path`, behave as before.

## Steps
1. Find the changelog file: `<app_path>/CHANGELOG.md` when scoped, else the repo-root `CHANGELOG.md` / `docs/CHANGELOG.md` (or as configured).
2. Determine the last entry's date or commit reference.
3. Run `git log --since=<last-entry-date> --no-merges --oneline` (scoped to `<app_path>` when set) and inspect commits since then.
4. Filter to **user-facing** changes only: new features, UX changes, visible bug fixes, removed features. Exclude refactors, deps, internal tooling, tests, CI.
5. If nothing user-facing has happened since the last entry, exit silently.
6. Write new entries in the project's configured changelog format and language. Match the tone and structure of existing entries exactly.

## Branch, commit, and open the PR
This task runs in **pull-request mode** (per `manifest.yml`). Create a feature branch, commit your changes there, push, and open a PR with the standardized title format. Ensure labels exist (idempotent), then attach them. End the PR body with the Night Shift footer.

```
# Create the branch (include app slug when scoped):
# scoped:
git checkout -b nightshift/changelog-<app-slug>-YYYY-MM-DD
# unscoped:
git checkout -b nightshift/changelog-YYYY-MM-DD

git add -A
# scoped commit:
git commit -m "nightshift(changelog): <app_path> — update for recent user-facing changes"
# unscoped commit:
git commit -m "nightshift(changelog): update for recent user-facing changes"

git push -u origin HEAD

gh label create nightshift --color "0e8a16" --description "Automated by Night Shift" 2>/dev/null || true
gh label create "nightshift:docs" --color "1d76db" --description "Night Shift docs bundle" 2>/dev/null || true

# scoped PR title:
gh pr create --title "nightshift/changelog: <app_path> — update for recent user-facing changes" \
  --label nightshift --label "nightshift:docs" \
  --body "$(cat <<'EOF'
## Summary
- <bullet per new entry>

## Source commits
- <list of commits used to derive entries>

---
_Run by Night Shift • docs/update-changelog_
EOF
)"
# unscoped PR title:
# gh pr create --title "nightshift/changelog: update for recent user-facing changes" \
#   --label nightshift --label "nightshift:docs" \
#   --body "..."
```

**Do not** modify `docs/NIGHTSHIFT-HISTORY.md` from this branch — the multi-runner wrapper appends the history row on `main` after you return your one-line result.

## Idempotency
- Never duplicate an entry. If the latest commits are already represented, exit.
- Overwrite drafts only if clearly marked as such — never rewrite published entries.
