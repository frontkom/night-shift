# Task 02 — User Manual

Generate or update end-user documentation derived from UI routes and components.

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: doc language, key pages, push protocol. If task 2 is not in the task list, exit.

## Steps
1. Locate the user manual (`docs/USER-MANUAL.md` or as configured). Create it if it does not exist.
2. Walk the project's UI routes (App Router pages, React Router routes, etc.) and key components for each configured **key page**.
3. For each page/feature, document:
   - What the user sees
   - What actions are available
   - What happens on each action (in user terms, not implementation terms)
4. Write in the configured **doc language**. Match the tone of any existing manual sections.
5. If the manual already covers a page and nothing in that page's source has changed since the last update, leave that section alone.

## Commit
```
git add <manual-file>
git commit -m "nightshift(docs): refresh user manual"
```
Push using the project's push protocol.

## Idempotency
- Skip pages whose source files have not changed since the last manual update (`git log -1 --format=%ct -- <page>` vs the manual's mtime/last commit).
- If nothing changed anywhere, exit silently.
