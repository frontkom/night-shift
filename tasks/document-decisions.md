# ADR (Architectural Decision Records)

Document genuinely significant architectural decisions. **The bar is high, and the default outcome is to exit silently.**

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: doc language, push protocol. If the dispatcher passed `allowed_tasks` and `document-decisions` is not in it, exit silently.

**Scoping.** This task is `scope: repo` in `manifest.yml`. ADRs describe repo-wide architectural choices, so even in a monorepo with `apps:` configured, this task runs **once per repo**, not once per app. Ignore any `app_path` passed by the multi-runner — the multi-docs-and-code-fixes wrapper will only dispatch this task during the first work-item of a repo.

## High bar — most nights should produce zero ADRs

ADRs are expensive: they commit the project to a narrative, they need to be kept true, and a low-value ADR dilutes the signal of the high-value ones. A decision is ADR-worthy **only if all of these hold**:

- **Reversing it would require a non-trivial rewrite or a coordinated migration** — not just swapping a library or flipping a config.
- **The *why* is non-obvious from reading the code**, and a future engineer would waste real time relitigating or accidentally undoing it without the ADR.
- **It reflects a deliberate trade-off between real alternatives.** Accepting a framework default, following a common pattern, or picking the obvious library does not qualify.
- **It is not already documented** in `README.md`, `ARCHITECTURE.md`, `CLAUDE.md`, `CONCEPT.md`, `TECH.md`, or similar.

**Not ADR-worthy — skip silently:**
- Minor library choices (lint plugins, date utilities, icon packs, test helpers).
- Formatting, folder naming, file layout, or code-style conventions.
- Following a framework's recommended pattern (Next.js App Router, Django apps, Rails conventions, etc.).
- Config values, env var names, version pins.
- Anything a reader can infer in ~60 seconds from the code itself.
- Retroactive documentation of decisions that are already obvious and uncontroversial.

When in doubt, **skip**. A silent night is the correct outcome on most runs. Opening a PR that only marginally helps costs reviewer time and erodes trust in Night Shift — that is a worse outcome than doing nothing.

## Steps
1. Look in `docs/adr/` at the **repo root** (create only if you have actually found an ADR-worthy decision — do not create the directory just to stay busy). Read existing ADRs to learn the project's format and numbering. Do not write ADRs inside an app subdirectory.
2. Scan the codebase and `git log` for candidates, then apply the **High bar** filter above. Good hunting grounds:
   - Significant framework / platform choices where a different choice would have forced a different architecture (e.g. "we picked event sourcing over CRUD", not "we use date-fns").
   - Notable architectural boundaries with real trade-offs (monorepo vs polyrepo, server-only data layer, a custom caching tier, a chosen consistency model).
   - Systems that were **removed or replaced** and whose absence is confusing without context.
3. For each candidate that **passes the high bar**, create `docs/adr/NNNN-<slug>.md` with:
   - Context (why was a choice needed, what alternatives existed)
   - Decision (what was chosen)
   - Consequences (trade-offs, things future contributors need to know)
4. Write in the configured **doc language**. Stay neutral — document, don't editorialize.
5. Cap output at **2 new ADRs per night**. Zero is expected and correct on most nights.

## Branch, commit, and open the PR
This task runs in **pull-request mode** (per `manifest.yml`). Create a feature branch, commit your changes there, push, and open a PR with the standardized title format. Ensure labels exist (idempotent), then attach them. End the PR body with the Night Shift footer.

```
git checkout -b nightshift/adr-YYYY-MM-DD

git add docs/adr/
git commit -m "nightshift(adr): document <decision-1>, <decision-2>"
git push -u origin HEAD

# Wrapper has already created the standard labels for this repo — just attach them.
gh pr create --title "nightshift/adr: document <decision-1>, <decision-2>" \
  --label nightshift --label "nightshift:docs" \
  --body "$(cat <<'EOF'
## Summary
- <bullet per ADR added, with one-line rationale>

## ADRs added
- docs/adr/<NNNN-slug>.md
- docs/adr/<NNNN-slug>.md (only if a second is genuinely warranted)

---
_Run by Night Shift • docs/document-decisions_
EOF
)"
```

**Do not** modify `docs/NIGHTSHIFT-HISTORY.md` from this branch — the multi-runner wrapper appends the history row on `main` after you return your one-line result.

## Idempotency
- Never overwrite existing ADRs. If a topic is already covered, skip it.
- If no decision clearly passes the high bar, exit silently. Do not pad, do not settle.
