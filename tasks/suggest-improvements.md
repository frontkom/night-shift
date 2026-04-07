# Task 04 — Suggestions

Analyze the codebase for improvement ideas to pitch to the client. This is a **discovery** task — do not change code.

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: doc language, push protocol. If task 4 is not in the task list, exit.

## Steps
1. Open or create `docs/SUGGESTIONS.md`.
2. Read existing suggestions so you don't repeat them.
3. Look for opportunities across:
   - UX rough edges (confusing flows, missing feedback states, unclear errors)
   - Quick wins (small features that would clearly help users)
   - Tech-debt that is starting to hurt velocity
   - Missing observability / monitoring
   - Onboarding gaps for new users
4. For each suggestion, write:
   - **Title** (1 line)
   - **Why** (the user/business value, 2-3 sentences)
   - **Effort** (rough size: S / M / L)
   - **Files involved** (so a human can find their way in)
5. Cap output at **3 new suggestions per night**.

## Commit
```
git add docs/SUGGESTIONS.md
git commit -m "nightshift(suggestions): add <N> ideas"
```
Push using the project's push protocol.

## Idempotency
- Never duplicate an existing suggestion. If a topic is already listed, skip it.
- If nothing new comes to mind, exit silently. Do not pad.
