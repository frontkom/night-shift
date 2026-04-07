# Task 01 — Changelog

Update the project's changelog if there are new user-facing changes since the last entry.

## Read project config first
Read `CLAUDE.md` for the **Night Shift Config** section: doc language, changelog format, push protocol. If task 1 is not in the task list, exit.

## Steps
1. Find the changelog file (`CHANGELOG.md`, `docs/CHANGELOG.md`, or as configured).
2. Determine the last entry's date or commit reference.
3. Run `git log --since=<last-entry-date> --no-merges --oneline` and inspect commits since then.
4. Filter to **user-facing** changes only: new features, UX changes, visible bug fixes, removed features. Exclude refactors, deps, internal tooling, tests, CI.
5. If nothing user-facing has happened since the last entry, exit silently.
6. Write new entries in the project's configured changelog format and language. Match the tone and structure of existing entries exactly.

## Commit
```
git add <changelog-file>
git commit -m "nightshift(changelog): update for recent user-facing changes"
```
Push using the project's push protocol.

## Idempotency
- Never duplicate an entry. If the latest commits are already represented, exit.
- Overwrite drafts only if clearly marked as such — never rewrite published entries.
