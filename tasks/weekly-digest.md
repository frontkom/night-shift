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

## Branch, commit, and open the PR
This task runs in **pull-request mode** (per `manifest.yml`). Create a feature branch, commit your changes there, push, and open a PR with the standardized title format. Ensure labels exist (idempotent), then attach them. End the PR body with the Night Shift footer.

```
git checkout -b night-shift/digest-YYYY-MM-DD

git add docs/NIGHTSHIFT-DIGEST.md
git commit -m "night-shift(digest): weekly metrics digest"
git push -u origin HEAD

# Wrapper has already created the standard labels for this repo — just attach them.

cat > /tmp/night-shift-pr-body.md <<'EOF'
## Summary
- Week ending <YYYY-MM-DD>
- <Total runs>: <ok> ok, <silent> silent, <failed> failed
- <Silent rate>%
- <PRs referenced count>

See `docs/NIGHTSHIFT-DIGEST.md` for the full digest.

---
_Run by Night Shift • docs/weekly-digest_
EOF

PR_URL=$(gh pr create --title "night-shift/digest: weekly metrics digest" \
  --label night-shift --label "night-shift:docs" \
  --body-file /tmp/night-shift-pr-body.md)
# Post-create ritual (spec: bundles/_multi-runner.md)
gh pr edit "$PR_URL" --add-label night-shift --add-label "night-shift:docs"
BODY=$(gh pr view "$PR_URL" --json body -q .body)
case "$BODY" in *'\n'*) printf '%s' "$BODY" | python3 -c "import sys;sys.stdout.write(sys.stdin.read().replace(chr(92)+chr(110),chr(10)))" > /tmp/night-shift-body-fix.md && gh pr edit "$PR_URL" --body-file /tmp/night-shift-body-fix.md ;; esac
gh pr merge "$PR_URL" --auto --squash 2>/dev/null || gh pr merge "$PR_URL" --auto || true
```

**Always use `--body-file`, never inline `--body`.** See `bundles/_multi-runner.md` → "PR body formatting".

**Do not** modify `docs/NIGHTSHIFT-HISTORY.md` from this branch — the multi-runner wrapper appends the history row on `main` after you return your one-line result.

## Idempotency
- This task overwrites the digest file each run — it is safe to re-run.
- If the history file is missing or has no recent entries, the digest simply says "No Night Shift activity this week."
