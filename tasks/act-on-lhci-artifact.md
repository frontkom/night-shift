# Act on Lighthouse CI artifact

Read the latest Lighthouse CI (LHCI) artifact for the project, identify **one** concrete budget violation or failed audit on a configured key page, and open a PR with a targeted fix. **Data-driven companion to `improve-performance`** — that task reads source heuristically; this one acts on real measurements.

## Read project config first

Read `CLAUDE.md` for **Night Shift Config**: key pages, test command, build command, default branch, push protocol. If the dispatcher passed `allowed_tasks` and `act-on-lhci-artifact` is not in it, exit silently.

This task is **opt-in via project config**. In the project's `CLAUDE.md` Night Shift Config:

```
- LHCI enabled: yes
- LHCI artifact source: github-actions   # or `vercel-comment` if the project doesn't upload an artifact
- LHCI workflow: lighthouseci.yml         # the workflow file name; default if omitted
```

If `LHCI enabled` is not `yes` or the project has no LHCI workflow, **exit silently**. This task does not configure LHCI — for that, see `docs/lighthouse-ci-vercel.md`.

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`), operate inside that app only:
- Read `key pages` from the scoped config (the `apps[]` entry for this app).
- Branch: `night-shift/lhci-fix-<app-slug>-YYYY-MM-DD`.
- PR title: `night-shift/lhci-fix: <app_path> — <one-line summary of the fix>`.

Without an `app_path`, behave as repo-scoped (top-level key pages, whole repo, no app slug).

## Pre-flight: don't stack PRs

Before downloading any artifact, check whether an open Night Shift LHCI-fix PR already exists for this scope:

```bash
gh pr list --search "night-shift/lhci-fix in:title" --state open
```

If one exists for the same app (or repo when unscoped), **exit silently** — do not stack PRs. Resume normal behaviour once the open PR is merged or closed.

## Language

- **PR title, body, and commit messages are written in English** so anyone in the company can review them, regardless of the product's user language.
- Any user-facing text touched by the fix (page titles, alt text, meta descriptions) stays in the project's configured doc language.

## High bar — default is silent

Open a PR **only** when:
1. The artifact contains a clear, concrete violation (budget exceeded with a specific page + audit ID), AND
2. The fix is small (single component / single file / single config tweak), AND
3. You can predict the measured improvement (e.g. "removing this client-side import drops the LCP page's JS bundle from 340 KB → 245 KB and should clear the LCP budget").

**Speculative or "this might help" tweaks do not qualify.** Most nights this task should exit silently — that is the correct outcome when LHCI is already passing or when violations are too diffuse to attribute to one fix.

## Steps

1. **Locate the latest artifact.**

   **GitHub Actions source** (`LHCI artifact source: github-actions`):
   ```bash
   # Find the most recent successful LHCI run on the default branch (or any branch if --branch unset)
   gh run list --workflow "${LHCI_WORKFLOW:-lighthouseci.yml}" --status success --limit 1 --json databaseId,headBranch,createdAt
   RUN_ID=$(gh run list --workflow "${LHCI_WORKFLOW:-lighthouseci.yml}" --status success --limit 1 --json databaseId --jq '.[0].databaseId')
   gh run download "$RUN_ID" --dir /tmp/lhci-artifact
   ```
   The artifact contains LHCI JSON reports (`lhr-*.json`) keyed by run + form factor (mobile / desktop) per the pattern in `docs/lighthouse-ci-vercel.md`.

   **Vercel-comment source** (when no artifact is uploaded): exit silently with a warning. The bot-comment-only setup doesn't give enough structured data; recommend switching to artifact upload via `docs/lighthouse-ci-vercel.md`.

2. **Parse the artifact** — read each `lhr-*.json` (one per page × form factor). Each report has:
   - `categories.performance.score` — the headline number
   - `audits.*` — individual audit results with `id`, `score`, `numericValue`, `displayValue`, `description`
   - `audits.*.details.items[]` — for opportunities, the specific resources/elements contributing

   Build a flat list of **failed audits with a knowable root cause** across all reports:
   - `largest-contentful-paint` numericValue > 2500 ms → check `details.items[]` for the LCP element
   - `cumulative-layout-shift` numericValue > 0.1 → check `metric-savings.CLS`
   - `total-blocking-time` numericValue > 200 ms → check `details.items[]` for long tasks
   - `unused-javascript` / `unused-css-rules` with savings > 50 KB → check `details.items[]` for the source URL
   - `render-blocking-resources` → check `details.items[]` for blocking URLs
   - `uses-optimized-images` / `modern-image-formats` / `uses-text-compression` → check `details.items[]` for unoptimised assets
   - `font-display` ≠ `swap` → font URLs in `details.items[]`
   - any **a11y category** audit with `score: 0` and a specific element in `details.items[]`

3. **Pick the highest-leverage one.** Tiebreakers:
   - Mobile beats desktop (mobile budgets are tighter and users skew mobile)
   - Pages earlier in the configured `key pages` list beat later ones
   - "Largest measured savings" (LCP delta, KB saved, ms saved) beats smaller
   - Concrete `details.items[]` entry pointing at a specific file beats diffuse audits

4. **Verify the fix is small.** Open the file(s) the audit points at. If the fix is:
   - One client-import → server-import migration → ✓ proceed
   - One image swap from JPG → AVIF / WebP → ✓ proceed
   - One font-loading directive → ✓ proceed
   - One `next/script` strategy swap → ✓ proceed
   - One dynamic import for a heavy client component → ✓ proceed
   - A multi-file refactor, framework upgrade, or architectural change → **exit silently** (this is the human's call, not Night Shift's)

5. **Apply the fix.** Edit the file(s) minimally. Don't reformat unrelated lines. Don't introduce new dependencies unless the audit explicitly requires one (e.g. `sharp` for image conversion in a Next.js project that doesn't already have it).

6. **Verify locally.** Run the project's build (`Build command:` in config) — abort the PR if the build fails. Run tests if `Test command:` is configured and the test suite is fast enough (skip if > 5 min). The full LHCI re-run happens on the PR's own preview deploy; don't try to reproduce it locally.

7. **Branch, commit, push, PR** following standard Night Shift conventions:

   ```bash
   # scoped:
   git checkout -b night-shift/lhci-fix-<app-slug>-YYYY-MM-DD
   # unscoped:
   git checkout -b night-shift/lhci-fix-YYYY-MM-DD

   git add -A
   git commit -m "night-shift(lhci-fix): <one-line summary>

   <2-3 sentence rationale citing the LHCI audit ID and measured violation>

   Source: LHCI run <run-id>, <page-url>, <mobile|desktop>.
   Audit: <audit-id>, score <X>, numericValue <Y> <unit>.
   Expected after fix: <predicted improvement>.
   "

   git push -u origin HEAD

   # Wrapper has already created the standard labels for this repo — just attach them.

   cat > /tmp/night-shift-pr-body.md <<'EOF'
   ## Plain summary
   <1-2 sentences in English. Who benefits and which page improved.>

   ## What the artifact showed
   - **Page**: <URL>
   - **Form factor**: <mobile | desktop>
   - **Audit**: <audit-id> ([Lighthouse audit ref](https://web.dev/articles/<audit-id>))
   - **Measured value**: <numericValue> <unit> (budget: <budget> <unit>)
   - **Source artifact**: LHCI run [<run-id>](<run-url>)

   ## Predicted impact
   <e.g. "Removing the client-side import of `lib/heavy-chart` should drop the LCP-page JS bundle by ~95 KB. Should clear the 200 KB mobile JS budget and improve LCP by ~600 ms on slow 4G.">

   ## Verification
   - [ ] CI green on the new PR's preview deploy
   - [ ] LHCI re-run on the preview deploy shows the audit now passing (auto-reported via PR comment)

   ---
   _Run by Night Shift • tasks/act-on-lhci-artifact_
   EOF

   # Stagger PR creation. Spec: bundles/_multi-runner.md → "PR creation throttle".
   LAST=/tmp/night-shift-pr-last-created
   if [ -f "$LAST" ]; then
     ELAPSED=$(( $(date +%s) - $(cat "$LAST") ))
     [ "$ELAPSED" -lt 90 ] && sleep "$((90 - ELAPSED))"
   fi
   PR_URL=$(gh pr create --title "night-shift/lhci-fix: <one-line>" \
     --label night-shift \
     --body-file /tmp/night-shift-pr-body.md)
   date +%s > /tmp/night-shift-pr-last-created
   # Post-create ritual — REQUIRED. See bundles/_multi-runner.md.
   gh pr edit "$PR_URL" --add-label night-shift
   BODY=$(gh pr view "$PR_URL" --json body -q .body)
   case "$BODY" in *'\n'*) printf '%s' "$BODY" | python3 -c "import sys;sys.stdout.write(sys.stdin.read().replace(chr(92)+chr(110),chr(10)))" > /tmp/night-shift-body-fix.md && gh pr edit "$PR_URL" --body-file /tmp/night-shift-body-fix.md ;; esac
   gh pr merge "$PR_URL" --auto --squash 2>/dev/null || gh pr merge "$PR_URL" --auto || true
   ```

   **Always use `--body-file`, never inline `--body`.** See `bundles/_multi-runner.md` → "PR body formatting".

## Idempotency

- One PR per audit, per branch. Don't bundle multiple LHCI findings — pick the best one.
- If a previous LHCI-fix PR for the same audit ID is still open, exit silently (covered by the pre-flight above).
- If the artifact shows the audit is already passing (regression-resistant), exit silently.

## Relationship to `improve-performance`

- `improve-performance` runs every week and reads source heuristically — it catches structural issues (N+1 queries, missing indexes, large client bundles imported by mistake) that don't always show up as LHCI failures.
- `act-on-lhci-artifact` runs only where LHCI is configured and acts on **measured** failures — it catches things only real Lighthouse runs can see (LCP element identification, CLS shifts, third-party blocking time on real network throttling).

Both can run on the same project without conflict — they operate from different evidence sources and the dedup pre-flight on each task's own slug prevents stacking.
