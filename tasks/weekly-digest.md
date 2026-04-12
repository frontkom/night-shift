# Weekly Metrics Digest

Summarize the past week's Night Shift activity into a digest with key metrics.

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: doc language, push protocol. If the dispatcher passed `allowed_tasks` and `weekly-digest` is not in it, exit silently.

**Scoping.** This task is `scope: repo` in `manifest.yml`. The digest covers all Night Shift activity across the repo, so even in a monorepo with `apps:` configured, this task runs **once per repo**, not once per app. Ignore any `app_path` passed by the multi-runner.

## Steps
1. Open `docs/NIGHTSHIFT-HISTORY.md` at the **repo root**. If it does not exist, write "No Night Shift activity this week" to `docs/NIGHTSHIFT-DIGEST.md`, commit, and exit.
2. Parse the history entries and filter to the **past 7 days** (relative to today's date).
3. If there are no entries in the past 7 days, write "No Night Shift activity this week" to `docs/NIGHTSHIFT-DIGEST.md`, commit, and exit.
4. Compute the following metrics from the filtered entries:
   - **Total runs by bundle** — count how many task runs occurred in each bundle (plans, docs, code-fixes, audits).
   - **Status breakdown** — count runs by outcome: ok (task made changes), silent (task found nothing to do), failed (task errored).
   - **PRs opened** — count of pull requests opened, with links if available from the history notes.
   - **Silent run rate** — percentage of total runs that ended as silent (found nothing to do). Format as `X%`.
5. Write the digest to `docs/NIGHTSHIFT-DIGEST.md` (overwrite the entire file, do not append). Use the following format:

```markdown
# Night Shift Digest

**Week ending:** YYYY-MM-DD

## Summary

| Metric | Value |
|--------|-------|
| Total runs | N |
| OK | N |
| Silent | N |
| Failed | N |
| Silent rate | X% |
| PRs opened | N |

## Runs by bundle

| Bundle | Runs | OK | Silent | Failed |
|--------|------|----|--------|--------|
| plans | … | … | … | … |
| docs | … | … | … | … |
| code-fixes | … | … | … | … |
| audits | … | … | … | … |

## PRs opened

- [PR title](link) — bundle / task
- …

_(or "None this week" if no PRs were opened)_

## Key takeaways

- 1–3 short bullet points noting anything interesting: high silent rates in a bundle, failures worth investigating, productive streaks, etc.
```

6. Write in the configured **doc language**. Keep takeaways factual and brief.

## Commit
```
git add docs/NIGHTSHIFT-DIGEST.md
git commit -m "nightshift(digest): weekly metrics digest"
```
Push using the project's push protocol.

## Idempotency
- This task overwrites the digest file each run — it is safe to re-run.
- If the history file is missing or has no recent entries, the digest simply says "No Night Shift activity this week."
