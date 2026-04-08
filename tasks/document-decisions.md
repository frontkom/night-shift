# ADR (Architectural Decision Records)

Document architectural decisions visible in code, config, and git history.

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: doc language, push protocol. If this task is not in the task list, exit.

**Scoping.** This task is `scope: repo` in `manifest.yml`. ADRs describe repo-wide architectural choices, so even in a monorepo with `apps:` configured, this task runs **once per repo**, not once per app. Ignore any `app_path` passed by the multi-runner — the multi-docs-and-code-fixes wrapper will only dispatch this task during the first work-item of a repo.

## Steps
1. Look in `docs/adr/` at the **repo root** (create if missing). Read existing ADRs to learn the project's format and numbering. Do not write ADRs inside an app subdirectory.
2. Scan the codebase and `git log` for decisions that are not yet documented:
   - Framework / library choices (auth, db, cache, queue, AI provider, etc.)
   - Notable architectural patterns (monorepo layout, server vs client boundaries, caching strategies)
   - Removed or replaced systems (often the most useful to record)
3. For each undocumented decision, create `docs/adr/NNNN-<slug>.md` with:
   - Context (why was a choice needed)
   - Decision (what was chosen)
   - Consequences (trade-offs, things to know)
4. Write in the configured **doc language**. Stay neutral — document, don't editorialize.
5. Cap output at **2 new ADRs per night** to avoid noise.

## Commit
```
git add docs/adr/
git commit -m "nightshift(adr): document <decision-1>, <decision-2>"
```
Push using the project's push protocol.

## Idempotency
- Never overwrite existing ADRs. If a topic is already covered, skip it.
- If no undocumented decisions remain, exit silently.
