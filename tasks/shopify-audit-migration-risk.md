# Audit migration risk (Shopify)

Run the project's pre-flight audit for "what apps will fire side effects on the next bulk import?" — Klaviyo flows, Judge.me review-request scheduling, channel-sync apps that push to Amazon/eBay/Walmart, etc. **One issue when known-risky apps are detected AND a migration-shape change appears in flight; otherwise silent.**

This task is Shopify-specific. Enable it for a project by selecting it during night-shift bundle setup.

The trigger for the May 2026 hovedsmann incident was Judge.me being told to "schedule requests for previous Shopify orders" — it used the Matrixify import date as the purchase date for ALL historical orders and queued 13,833 emails. This task surfaces those apps BEFORE a bulk import is scheduled.

## Read project config first

Read `CLAUDE.md` for **Night Shift Config**: default branch. If the dispatcher passed `allowed_tasks` and `shopify-audit-migration-risk` is not in it, exit silently.

## High bar — default is silent

Two AND'd preconditions must both hold:

1. The project has known-risky apps installed (per `audit_migration_risk.py` exit code).
2. Recent commits in the default branch's last 7 days touch migration shape — `scripts/tasks/seed*`, `scripts/tasks/migrate_*`, `migration/intermediate-*.json`, or new files matching `*matrixify*`. If neither has been touched, no import is being prepared and there's no urgency.

**If either precondition fails, exit silently.** Most nights, no import is being prepared.

If a `migration-risk` issue is already open (filed by this task on a previous night), update it rather than opening a duplicate.

## Steps

1. **Run the project's audit:**
   ```
   python -m scripts.tasks.audit_migration_risk --json > /tmp/migration-risk.json
   ```
   The script exits 1 if known-risky apps are installed (Klaviyo, Judge.me, Yotpo, Loox, Smile.io, Amazon/eBay sync, etc.); exits 0 if clean.

   If the script doesn't exist in this project (e.g., it hasn't been synced from `claude-shopify-boilerplate`), exit silently — the project isn't on the boilerplate yet.

   If the script exits 0 (no risky apps), exit silently. There's nothing to warn about.

2. **Detect migration-shape changes** in the last 7 days:
   ```
   git log --since="7 days ago" --name-only --pretty=format: | sort -u | grep -E "^(scripts/tasks/seed|scripts/tasks/migrate_|scripts/tasks/build_|migration/intermediate)"
   ```
   If empty, exit silently.

3. **Check for an existing open issue** with label `migration-risk`:
   ```
   gh issue list --label "migration-risk" --state open --json number,body
   ```
   If one exists and the audit findings haven't changed (compare against the existing body's app list), exit silently. If the findings have changed (a new app was installed since the last issue was filed), update the existing issue with a comment rather than opening a new one.

4. **Open or update the issue.** Title: `Pre-flight: known-risky apps detected before pending migration`. Body:
   ```
   cat > /tmp/migration-risk-body.md <<'EOF'
   ## Plain summary
   <1 sentence in English. "Klaviyo + Judge.me are installed and recent commits touch migration scripts — pause flows in those apps before running the next import to avoid the email-blast scenario."

   ## What the audit found

   <inline JSON output from audit_migration_risk.py — list of installed known-risky apps with per-app risk notes>

   ## Why this issue exists right now

   Recent commits touch migration shape (last 7 days):

   <git log output from step 2>

   The project's risk-app list is non-empty AND there's a pending import. Either condition alone wouldn't trigger; the combination did.

   ## Pre-flight checklist (per docs/MIGRATION_RUNBOOK.md Phase 1)

   For each app listed above:
   - [ ] Configure to ignore the import (tag-based suppression on tag:migration, or pause flows in the app's own dashboard)
   - [ ] Toggle off Settings → Notifications templates that fire on the resource type being imported
   - [ ] Set acceptsMarketing=false on imported customers (verify this is in the import script)
   - [ ] Pause Shopify Flow rules that trigger on affected events
   - [ ] Verify post-import: each app's dashboard shows ~0 sends in the 30 minutes after the import

   ## Reference

   The May 2026 hovedsmann incident: 13,833 review-request emails queued for orders going back 10 years because Judge.me was told to schedule for "previous Shopify orders" without auditing what that meant. See claude-shopify-boilerplate `docs/MIGRATION_RUNBOOK.md` for the full runbook.

   This issue closes automatically when either:
   - The risky-app list goes to zero (apps were uninstalled), OR
   - The migration commits stop appearing in the recent-commits window (the import landed safely)

   ---
   <Night Shift footer per repo template>
   EOF

   gh issue create \
     --title "Pre-flight: known-risky apps detected before pending migration" \
     --label "migration-risk,claude-monitor" \
     --body-file /tmp/migration-risk-body.md
   ```

5. **Don't open a PR.** This task only files issues — it never modifies code. The fix is in the merchant's app dashboards (Klaviyo, Judge.me, etc.), not in code. The issue is the prompt for the human to act before the next import.

## Why this is a separate task vs being part of an import script

The audit is also a function call inside `safe_mutate.bulk_import_preflight()` — if a script that does bulk imports calls preflight, the audit runs synchronously and the script halts on risk. That handles the case "developer is about to run a known import script." But many imports go through Matrixify (an external CSV upload tool, not our framework). Night Shift catches the case "someone is preparing a Matrixify import" by watching the commit pattern, not the script execution.

## Cross-references

- claude-shopify-boilerplate `scripts/tasks/audit_migration_risk.py` — the audit engine
- claude-shopify-boilerplate `docs/MIGRATION_RUNBOOK.md` — Phase 1 pre-flight + per-app suppression patterns
- claude-shopify-boilerplate `scripts/lib/safe_mutate.py:bulk_import_preflight` — the in-script equivalent
- The May 2026 hovedsmann Judge.me incident is documented in that project's `docs/Briefing - Martine.md`.
