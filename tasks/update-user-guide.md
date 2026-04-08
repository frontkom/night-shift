# User Manual

Generate or update end-user documentation derived from UI routes and components.

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: doc language, key pages, push protocol. If this task is not in the task list, exit.

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`):
- Prefer a per-app user manual at `<app_path>/docs/USER-MANUAL.md`. Create it if missing.
- If the app has no manual but the repo root does (`docs/USER-MANUAL.md` or as configured), write to the repo-root manual **and** put the app's sections under a heading that names the app (e.g. `## web — Dashboard`).
- Walk only UI routes and components under `<app_path>`. Read `key pages` from the scoped config.
- Commit message names the app: `nightshift(docs): <app_path> — refresh user manual`.

Without an `app_path`, behave as before.

## Steps
1. Locate the user manual: `<app_path>/docs/USER-MANUAL.md` when scoped, else `docs/USER-MANUAL.md` (or as configured). Create it if it does not exist.
2. Walk the project's UI routes (App Router pages, React Router routes, etc.) and key components for each configured **key page**. Restrict the walk to `<app_path>` when scoped.
3. For each page/feature, document:
   - What the user sees
   - What actions are available
   - What happens on each action (in user terms, not implementation terms)
4. Write in the configured **doc language**. Match the tone of any existing manual sections.
5. If the manual already covers a page and nothing in that page's source has changed since the last update, leave that section alone.

## Commit
```
# scoped:
git commit -m "nightshift(docs): <app_path> — refresh user manual"
# unscoped:
git commit -m "nightshift(docs): refresh user manual"
```
Push using the project's push protocol.

## Idempotency
- Skip pages whose source files have not changed since the last manual update (`git log -1 --format=%ct -- <page>` vs the manual's mtime/last commit).
- If nothing changed anywhere, exit silently.
