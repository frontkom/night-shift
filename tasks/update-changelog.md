# Changelog

Update the project's changelog if there are new user-facing changes since the last entry.

## Read project config first
Read `CLAUDE.md` for the **Night Shift Config** section: doc language, changelog format, push protocol. If this task is not in the task list, exit.

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

## Commit
```
# scoped:
git commit -m "nightshift(changelog): <app_path> — update for recent user-facing changes"
# unscoped:
git commit -m "nightshift(changelog): update for recent user-facing changes"
```
Push using the project's push protocol.

## Idempotency
- Never duplicate an entry. If the latest commits are already represented, exit.
- Overwrite drafts only if clearly marked as such — never rewrite published entries.
