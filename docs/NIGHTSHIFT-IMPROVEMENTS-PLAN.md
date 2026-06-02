# Night Shift improvements — audit-driven plan

<!-- night-shift: keep -->

A phased plan for boosting Night Shift's effectiveness as a Frontkom revenue engine. Driven by:

1. A multi-phase audit (9 lenses × 75 candidate ideas × adversarial critique → 10 specs, 2026-06-02).
2. Live evidence from one weeknight on `frontkom/frisk` (PRs #1141–#1146, 2026-06-02).

The frisk night was instructive. Six PRs landed and the quality is high — every body uses `## Plain summary`, real verification, footers, beacon, self-review note. What did NOT land tells the story:

- No `night-shift/deps:` PR. `dep-audit` exists in `manifest.yml:225` but the picker in `skills/night-shift/SKILL.md` Step 2 (~lines 113–145) hardcodes 11 task ids while `manifest.yml` has 18 — it cannot be selected. `lhci-fix`, `lint-baseline`, `flake` are in the same hole.
- No `night-shift/plan:` PR. The repo has plan files but the build routine evidently found nothing pending, or the picker did not include `build-planned-features` for this repo. Either way, the highest-leverage bundle produced zero output last night.
- No measured-impact PR class. Every code-touching PR (#1142 a11y, #1143 bug, #1141 tests) is heuristic — sourced from reading code, not from a measurement signal. The bodies cannot say "47 users hit this error, now fixed." PMs cannot defend them as billable retainer line items.
- Five PR bodies cite Vercel preview-deploy bypass and `--no-verify` because of a pre-existing failing test on `main`. Reviewer trust takes a hit every time the body footer mentions hook-skipping.

The phases below close those gaps in priority order. Phases 1–3 are this week's slate; 4–6 are the next 2–4 weeks; 7–9 are long-horizon bets that depend on the earlier phases landing.

## Source artifacts

- Audit roadmap: synthesized from 104 subagents in workflow `wf_00b36c1f-768` on 2026-06-02.
- Live evidence: https://github.com/frontkom/frisk/pulls (PRs #1141–#1146).
- Canonical surface (verified 404 at audit time): https://frontkom.github.io/night-shift/.
- Mirror surface (verified 200, personal account): https://perandre.github.io/ns/.

## Phase 1 — Stop the credibility leak: canonical Pages + em-dash hydration

**Goal:** `frontkom.github.io/night-shift/` returns 200, OG image renders, landing-page stats show honest em-dashes instead of fabricated `178` / `~71h`.

**Why now:** Every external link to the agency story (LinkedIn posts, sales decks, RFPs, the README install instructions) lands on a 404. The mirror at `perandre.github.io/ns/` works but lives on a personal account — wrong artifact for an agency story. The hardcoded `178 PRs / ~71h` stats next to a dead `./dashboard/` link compound the credibility problem.

**Steps:**

1. Edit `index.html` lines 1469 and 1474. Replace `<div class="value is-gradient">178</div>` with `<div class="value is-gradient" data-stat="prs-opened">—</div>` and the `~71h` value with `data-stat="agent-hours">—</div>`. Remove or comment the dead `./dashboard/` link until Phase 5 lands.
2. Create `.github/workflows/pages.yml` with three jobs: `build` (no-op for a static site), `deploy` (uses `actions/deploy-pages@v4` with `actions/upload-pages-artifact@v3`), `smoke` (curls `/` and `/night-shift.png` with 5× retry @ 6s backoff for CDN propagation).
3. File a GitHub Issue on `frontkom/night-shift` titled `Enable GitHub Pages on frontkom/night-shift (org-admin)` and assign to whoever holds frontkom org-admin. The workflow is inert until **Settings → Pages → Source** is flipped to `GitHub Actions`.
4. After canonical Pages is green for one full week, retire the `git push mirror main` step from `AGENTS.md`. Mirror is the rollback path during burn-in.

**Acceptance criteria:**

- [ ] `curl -sS -o /dev/null -w '%{http_code}\n' https://frontkom.github.io/night-shift/` returns `200`.
- [ ] OG image renders in the Twitter/LinkedIn card validators (open-graph image URL resolves).
- [ ] `grep -n '178\|~71h' index.html` returns no results.
- [ ] `pages.yml` runs on push to `main`; smoke job passes.
- [ ] Pages-enablement issue is filed and assigned.

**Open questions:**

- Will org admin enable Pages on a `frontkom/*` repo? Confirm before sinking the implementation work.
- Is the marketing copy on `index.html:1587` ("2.25 MNOK/month") something Frontkom is comfortable shipping under the canonical URL, or does it need a revision pass first?

## Phase 2 — Manifest-driven picker + VALID_SLUGS gap fix

**Goal:** The setup wizard surfaces every task `manifest.yml` declares (today: 18). `VALID_SLUGS` matches every `slug:` field in `manifest.yml`.

**Why now:** Two real bugs, one root cause. The picker and the slug allowlist were hand-written and have rotted. Tasks Frontkom already built — `dep-audit`, `act-on-lhci-artifact`, `lint-baseline-shrink`, `find-flaky-tests` — cannot be selected during setup, so no client install can subscribe to them. `dep-audit` alone is a recurring CVE-pinning retainer the agency could sell to every Drupal/Next.js client tomorrow. Separately, `VALID_SLUGS` at `bundles/_multi-runner.md:334` omits `lhci-fix` and `flake` (real manifest slugs at `manifest.yml:220` and `:240`), so every LHCI and flake PR emits an `ERROR: PR title does not match…` stderr line. Reviewers learn to ignore the title-validator signal. Both are mechanical fixes.

**Steps:**

1. Add `lhci-fix` and `flake` to `VALID_SLUGS` in `bundles/_multi-runner.md` line 334. Also extend the prose enumeration at line 259 so the two lists stay in sync.
2. Add optional fields to the manifest task schema (documented in `manifest.yml`'s header comment): `picker_hidden: bool` (default `false`), `picker_default: bool` (default `true`), `bundle_group: string` (optional, overrides default picker grouping by `bundle:`).
3. Rewrite `skills/night-shift/SKILL.md` Step 2 (lines ~113–145) to derive picker groups from `manifest.yml` at runtime. Group by `bundle:` title; filter out `picker_hidden: true`; only surface a task if `bundles/multi-<bundle>.md` exists (this keeps shopify hidden until its routine ships); default-check based on `picker_default`.
4. Mark `find-flaky-tests` with `picker_default: false` to ship off-by-default for safety (it's the most opinionated audits task).
5. Bump `NIGHT_SHIFT_VERSION` to `2026-06-02a` in both `skills/night-shift/SKILL.md` line 9 (frontmatter `version:`) and line 14 (HTML comment) per `AGENTS.md`.

**Acceptance criteria:**

- [ ] Next `/night-shift` invocation surfaces all 18 tasks (minus any with `picker_hidden: true`).
- [ ] `manifest.yml` is the only place that declares which tasks exist; adding a 19th task does not require a `SKILL.md` edit.
- [ ] `VALID_SLUGS` matches the set of `slug:` values in `manifest.yml` (verify with a one-liner in the PR description).
- [ ] No `ERROR: PR title does not match…` stderr lines emitted on any task that uses an existing slug.
- [ ] Running `/night-shift` → `Change tasks for a repo` shows `dep-audit`, `act-on-lhci-artifact`, `lint-baseline-shrink`, `find-flaky-tests` as selectable.

**Open questions:**

- Should the picker re-fetch `manifest.yml` on every run, or cache for the session? (Setup runbook already caches — keep that.)
- Do we want a `picker_warning:` field for tasks that need extra confirmation (the current "audits open PRs nightly" warning is hardcoded in Question 3 — could move to manifest)?

## Phase 3 — `fix-from-sentry` (XS variant: GitHub Issues label path) + ADR 0003

**Goal:** Night Shift's first measured-impact PR class. Body sentence — "47 users hit this error in the last 24 hours, now fixed" — is the invoice line.

**Why now:** `act-on-lhci-artifact` proved measurement-driven PRs convert better than heuristic ones. Sentry is the same pattern on the highest-volume signal source agencies see. Most Frontkom client repos already have the Sentry → GitHub Issues integration installed with the default `sentry` label. The XS path consumes existing GitHub Issues — no MCP, no env vars, no parse-merge-rewrite churn. The L-effort MCP path (rejected by the audit) can come later if/when Sentry MCP stabilizes.

**Steps:**

1. Write `docs/adr/0003-data-driven-fix-tasks.md` establishing the pattern: any `fix-from-X` task consumes an existing channel (no new auth), enforces a quantitative high-bar (occurrences ≥10, distinct users ≥3, last-seen ≤24h, in-scope frame), opens at most one PR per repo per night, observes a 30-day per-fingerprint cooldown, default-silent.
2. Write `tasks/fix-from-sentry.md` (slug: `sentry`, bundle: `audits`, scope: `app`, needs: `[test, build]`). Mirror the `tasks/find-bugs.md` structure: Setup → Discovery (`gh issue list --label sentry`) → Filter (quantitative high-bar) → Repro (write failing test that throws the same error) → Fix → Open PR with `Closes #<n>` and `sentry-fingerprint: <fp>` in the body footer.
3. Add the manifest entry under `bundle: audits`, `order: 1.5` (between `find-security-issues` and `find-bugs`).
4. Add `sentry` to `VALID_SLUGS` (same commit as the `lhci-fix` / `flake` additions in Phase 2 if Phase 2 has not yet shipped; otherwise standalone).
5. Bump `NIGHT_SHIFT_VERSION`.

**Acceptance criteria:**

- [ ] ADR 0003 explains the pattern and is referenced from `tasks/fix-from-sentry.md`.
- [ ] On a repo with `gh issue list --label sentry --state open` returning ≥1 qualifying issue, the task opens one PR with: failing-test → fix → green CI → `Closes #<n>` and `sentry-fingerprint: <fp>` in the body.
- [ ] On a repo with no `sentry`-labelled issues, the task exits silently (`status: silent`, note `no qualifying sentry issues`).
- [ ] PR body's first sentence begins with the affected-users count (e.g. `47 users hit this error in the last 24 hours…`).
- [ ] 30-day per-fingerprint cooldown: re-running the task does not re-open a PR for the same fingerprint within 30 days.

**Open questions:**

- Where to store the per-fingerprint cooldown state? Options: a `.night-shift-cooldown` file in the target repo (committed, like `.vendor-baseline` in the shopify bundle), a tag/label scheme on the Sentry GitHub Issues themselves, or a comment on the closing PR. The audit favored the closing-PR comment approach — it requires no new file.
- Which Frontkom client repos currently have Sentry → GitHub Issues installed? File a parallel ticket to install it on the top 5 retainers before this task ships, so it has work on night 1.

## Phase 4 — Morning digest (opt-in 5th routine)

**Goal:** Convert the morning routine from `gh pr list --label night-shift` (a developer command) to a Slack/Teams message and a secret gist (a PM artifact).

**Why now:** Once Phase 3 ships, individual PRs say "47 users hit this." But there is no aggregator. PMs running client engagements still have nothing to paste into a weekly status email. The digest converts the existing per-PR `## Plain summary` blocks (already enforced) into a one-paste PM workflow. Silent on nights with zero PRs.

**Steps:**

1. Add `bundle: digest` to `manifest.yml`, plus a single task `night-digest`.
2. Create `bundles/digest.md` and `bundles/multi-digest.md` (wrapper).
3. Routine fires at `0 6 * * 1-5` UTC (08:00 Europe/Oslo). Walks all configured repos. For each, runs `gh pr list --label night-shift --state open --search 'created:>=YYYY-MM-DD'` (yesterday's date). Extracts the first paragraph under `## Plain summary` for each PR. Groups by repo + slug.
4. POST the digest to `NIGHT_SHIFT_WEBHOOK` (configured as a Claude Code routine env var, falls back to no-op). Also publish as a secret GitHub gist so the URL is shareable.
5. Update the setup runbook in `skills/night-shift/SKILL.md`: opt-in Yes/No question per install ("Want a morning digest?"). Existing 4-routine installs do NOT auto-upgrade — surface the opt-in in `Add a repo` and `Change tasks for a repo` flows only.
6. Bump `NIGHT_SHIFT_VERSION`.

**Acceptance criteria:**

- [ ] A new opt-in routine `night-shift-digest` can be created by users who run `/night-shift` after this lands.
- [ ] On a night with PRs, the webhook receives a structured message: per-repo block, per-slug subgroup, first sentence from each PR's `## Plain summary`.
- [ ] On a night with zero qualifying PRs across all configured repos, the digest sends nothing (silent).
- [ ] Existing 4-routine installs do not see any new routine until they explicitly run the opt-in.
- [ ] The secret gist URL is captured in the routine's run summary table.

**Open questions:**

- Slack vs Teams vs both? Frontkom uses Slack — start there.
- Should the digest also include yesterday's *merged* NS PRs (the work that landed) or only newly-opened ones? PM emails care about merged.

## Phase 5 — Local snapshot dashboard

**Goal:** Replace the dead `./dashboard/` link on the landing page with a real surface. Public URL PMs share in monthly retainer reviews.

**Why now:** Phase 1 makes the canonical Pages URL alive. Phase 3 + Phase 4 produce enough real data to populate widgets honestly. Building the dashboard before those phases land means rendering against three repos and one frisk-style night.

**Steps:**

1. Add a `snapshot` GitHub Action that runs daily at 06:00 UTC. Queries `gh pr list --label night-shift --state all --limit 1000 --json …` across configured repos (configured via `.github/snapshot-repos.yml`). Parses the `_Routine started:` beacon the multi-runner already stamps.
2. Write `dashboard/snapshot.json` with the parsed data. Commit to a `snapshot` branch (kept fresh, never merged to `main` — avoids history noise).
3. Build `dashboard/index.html` as a vanilla-JS page that fetches `snapshot.json` and renders four widgets: tonight's PRs, last-7-nights bar chart, per-task merged-vs-closed, per-repo activity.
4. **No fabricated economics.** `agent_hours_estimate` is real wall-clock from beacon to merge, not a per-task `estimated_minutes_saved` field. Defer the NOK-equivalent card to Phase 9.
5. Re-enable the dashboard link on `index.html` and replace the em-dash hydration in Phase 1 with real values pulled from `snapshot.json`.

**Acceptance criteria:**

- [ ] `https://frontkom.github.io/night-shift/dashboard/` returns 200.
- [ ] The dashboard renders without JS errors on Chrome, Firefox, Safari (no framework, no build step beyond `actions/upload-pages-artifact`).
- [ ] Widgets reflect real data from `gh pr list` queries, not hardcoded values.
- [ ] The landing page `data-stat` em-dashes hydrate from `snapshot.json`.
- [ ] No `estimated_minutes_saved` or NOK-equivalent fields appear on the dashboard (deferred to Phase 9).

**Open questions:**

- Should `dashboard/snapshot.json` be public (anyone can scrape it) or gated? Public makes the data shareable; gated requires an auth proxy.
- Which repos populate the dashboard? Configure via `.github/snapshot-repos.yml`. Default to the canonical demo + perandre's repos for the initial run.

## Phase 6 — Self-review as real GitHub review event

**Goal:** Self-review pass writes a real `gh pr review --comment` event instead of splicing one of three canned strings into the PR body.

**Why now:** The current pattern (`bundles/_multi-runner.md` lines ~415–443) writes one of three boilerplate strings into the PR body via a python splice. No independent timestamp evidence the review actually ran after the body was written, contention with the body sweep, body bloat. Switching to `gh pr review --comment --body-file` posts a structured checklist as a real GitHub review event (distinct timestamp, conversation entry), keeps a one-line `_Self-review: see review comment <url>_` pointer in the body.

**Steps:**

1. Update `bundles/_multi-runner.md` Self-review section: after the review + optional revision, post the structured note via `gh pr review "$PR_URL" --comment --body-file /tmp/night-shift-self-review.md`. NEVER use `--request-changes` — same-author 422 risk.
2. Replace the body splice with a single line: `_Self-review: see review comment <comment-url>_` inserted before the body footer.
3. Capture the review's comment URL from the `gh pr review` output and embed it in the line above.
4. Spike against the routine identity in a sandbox before merging — confirm `Claude <noreply@anthropic.com>` can post review comments on its own PRs.
5. Bump `NIGHT_SHIFT_VERSION`.

**Acceptance criteria:**

- [ ] Every code-touching NS PR has a real review comment from the routine identity, with a distinct timestamp.
- [ ] The PR body has a one-line `_Self-review: see review comment <url>_` pointer, not a 3-sentence boilerplate block.
- [ ] No `422 Unprocessable Entity` errors from `gh pr review` in routine logs.
- [ ] The body sweep in `_multi-runner.md` no longer touches the self-review section.

**Open questions:**

- If `gh pr review --comment` is rate-limited or fails, do we fall back to the old body-splice or skip the note? Lean toward skip — the PR is already created and armed.

## Phase 7 — Drupal vertical bundle (proof point: `drupal-security-advisories`)

**Goal:** Add a `drupal` bundle to the manifest with `drupal-security-advisories` as the first task. If proven, expand to 4 more Drupal-specific tasks.

**Why now:** Frontkom is a Drupal agency. `manifest.yml` has a `shopify:` bundle with two specialized tasks; zero Drupal tasks. Drupal-specific maintenance (contrib module security, drush updb migration checks, drush config:status drift, drupal-rector deprecated API hits, Composer 2.x constraint resolution) is exactly the high-volume nightly work Frontkom would bill for. The shopify bundle proves vertical bundles are easy to add and that target repos can ship helper scripts (the `claude-shopify-boilerplate` pattern).

**Steps:**

1. Add `bundle: drupal` to `manifest.yml` (`schedule_hint: weekly`, `parallelism: independent`, `stop_on_failure: false`, opt-in per project).
2. Document the opt-in mechanism: `bundles: [drupal]` in the target project's `CLAUDE.md` Night Shift Config block, same shape as the shopify opt-in.
3. Write `tasks/drupal-security-advisories.md` (slug: `drupal-cve`, scope: `app`). Polls drupal.org's security feed (RSS or JSON), cross-references against `composer.lock`, opens PRs pinning vulnerable contrib modules to safe versions.
4. Create `bundles/drupal.md` and `bundles/multi-drupal.md`.
5. Ship behind `picker_hidden: true` (opt-in via `CLAUDE.md` only, not the picker) for the first 4 weeks while we measure merge rate.

**Acceptance criteria:**

- [ ] One Frontkom Drupal client repo (intranett or similar) is opted in.
- [ ] After 4 weeks, the task has opened ≥2 merged PRs/week from this single task on the opt-in repo.
- [ ] If yes: graduate `drupal-security-advisories` to `picker_hidden: false` and schedule the next 4 Drupal tasks (drush-updb, config-drift, rector, composer-constraints).
- [ ] If no: write a postmortem in `docs/adr/` and either pivot the task design or close out the vertical bundle thesis.

**Open questions:**

- Does drupal.org publish a structured security feed Night Shift can poll without auth? (If not, write a small helper in the opt-in repo to fetch+normalize.)
- Should each Drupal task scope: `app` or `repo`? Drupal monorepos are rare; `scope: repo` is probably right for all five Drupal tasks.

## Phase 8 — Telemetry-intake task family

**Goal:** `fix-from-{datadog,axe-ci,k6,codeql,gsc-crawl}` — copy-paste-substitute of Phase 3's pattern across other measurement sources.

**Why now:** Once Phase 3 establishes the pattern (consume existing data channel → quantitative high-bar → measured-impact PR), each additional data source is mechanical. axe-CI for accessibility (replaces the heuristic `improve-accessibility`), k6 for perf regressions (data-driven sibling to `improve-performance`), CodeQL for security (sibling to `find-security-issues`), GSC crawl errors for SEO (sibling to `improve-seo`). Each measurement-driven task systematically outperforms its heuristic sibling on merge rate.

**Steps (dependent on Phase 3 + 30 days of merge-rate data):**

1. Measure `fix-from-sentry` 30-day merge rate vs `find-bugs` on the same set of repos.
2. If merge-rate ratio >2×, schedule the next 4 telemetry-intake tasks. Use ADR 0003 as the contract.
3. For each new task, identify the channel: axe-CI publishes artifacts to GitHub Actions; k6 publishes to a dashboard; CodeQL writes alerts to the GitHub Security tab; GSC requires a `GSC_*` env var on the routine.
4. Where the channel is GitHub-native (axe-CI artifact, CodeQL alert), use the GitHub API. Where it is external (k6, GSC), require the user to install a sidecar that writes to `gh issue create --label <channel>` — same pattern as Sentry.
5. Deprecate the heuristic siblings as their telemetry counterparts mature. (Slow deprecation: mark with `picker_default: false` first, then add a `superseded_by:` field in `manifest.yml`, then eventually remove.)

**Acceptance criteria (per task):**

- [ ] Each task self-skips silently when the data channel is absent.
- [ ] Each task's PR body opens with a measurement (`X users`, `Y failed crawls`, `Z regression %`) — that sentence is the invoice line.
- [ ] At 30-day measurement, each telemetry-driven task has a ≥2× merge rate vs its heuristic sibling.

**Open questions:**

- Heuristic siblings have value too (catch what telemetry misses). Deprecate or coexist? Lean toward coexist, with telemetry-driven scoring as the default in the picker.

## Phase 9 — Monthly client quality digest as a billable retainer line item

**Goal:** Productize the digest + dashboard + measured-impact PRs into a monthly per-client PDF report. The artifact that justifies a retainer-tier upsell.

**Why now:** Once Phases 3, 4, 5, 8 land, the components exist. Frontkom's existing maintenance-retainer clients pay first (the surface they already pay for becomes more visibly worth its price). New clients pay next, in pitches where the report replaces the current "trust us, we use AI overnight" sales motion.

**Steps:**

1. Add a `report` mode to `tasks/update-changelog.md` (or write a new `tasks/monthly-client-report.md`) that walks the previous month's NS PRs for a single client repo.
2. Generate a PDF report with: PRs shipped, measured impact (`287 users impacted` aggregated from Sentry-fed PRs), CVEs closed (from `dep-audit`), estimated dev-hours saved (real wall-clock from the beacon, NOT fabricated `estimated_minutes_saved`), per-task merge rate.
3. Run on the first Monday of every month at 09:00 UTC per opted-in client. POST to `NIGHT_SHIFT_REPORT_WEBHOOK`. Optionally email to the PM list configured per repo.
4. Brand the report (Frontkom logo, brand colours, signature block). Use `puppeteer` or similar for HTML → PDF.

**Acceptance criteria:**

- [ ] After 60 days of `fix-from-sentry` running on 5 client repos, attempt to generate one client's monthly report from `gh` + `snapshot.json` alone.
- [ ] If the report is readable by a non-technical client stakeholder without manual rewriting, the productized version is shippable.
- [ ] Measure: % of generated reports the PM ships verbatim vs has to rewrite. Target: ≥75% verbatim within 90 days.

**Open questions:**

- Pricing model for the retainer-tier upsell — flat monthly fee, per-merged-PR fee, or hybrid? Frontkom partners decide outside this plan.
- Should the report be co-branded with the client's logo? Default to Frontkom-branded; offer co-branding as an enterprise-tier option.

## What this plan deliberately rejects

The audit surfaced ~25 ideas the adversarial critique killed. Notable rejections (do not re-pitch unless circumstances change):

- **Sentry MCP-connector variant of `fix-from-sentry`** (L effort). Phase 3 collapses to XS via the GitHub-Issues-label path. The MCP variant requires parse-merge-rewrite for `mcp_connections`, a new long-lived auth surface, and adds routine-update risk. Defer until/unless Sentry MCP stabilizes and the XS variant proves the demand.
- **Standardize structured silent-reasons across 22 task files**. Real diagnosis (silent is overloaded across 7 failure modes) but no downstream reader consumes the codes today. Schema tax for a hypothetical consumer. Revisit if/when the dashboard (Phase 5) needs to surface silent-reason distributions.
- **Local static dashboard as Week-1 work**. Right idea, wrong sequencing — needs canonical Pages alive (Phase 1) AND real data (Phase 3) to be honest.
- **Adversarial second-pass reviewer subagent before PR opens**. Higher cost (extra subagent dispatch per PR), unclear evidence the same-model-different-prompt setup catches what one-pass misses. Phase 6 (real GitHub review event) gets most of the credibility win.
- **Auto-retire / auto-recommend tasks based on fleet-wide merge rate**. Requires fleet-wide telemetry that does not exist yet (Phase 5 is the precondition). Premature.
- **GitHub Actions backend ("second backend" the skill copy promises)**. Skill copy drift, not a real product gap. Either ship a reusable workflow or revise the skill copy to be honest about the single-backend reality.

## Risks and caveats (apply to the plan as a whole)

- Pages enablement on `frontkom/night-shift` depends on a Frontkom org-admin click. If org policy forbids, Phase 1 collapses and the mirror push protocol stays in `AGENTS.md`.
- `fix-from-sentry` needs Sentry → GitHub Issues installed on target client repos. Open a parallel ticket to install it on the top 5 retainers before Phase 3 ships.
- Every phase that adds a new YAML field to `<night-shift-config>` must survive parse-merge-rewrite (`SKILL.md:277`). Phases 1, 2, 3, 6 deliberately add zero new fields. Phase 4 adds an opt-in digest configuration; design that field carefully.
- The mirror push protocol stays in `AGENTS.md` for one-week burn-in after Phase 1 lands. Mirror is the rollback path.
- The routine-start beacon (`bundles/_multi-runner.md` lines ~80–93) is doing real work for no real consumer today (`perandre/ns-dashboard` is 404). Do not delete the beacon plumbing — Phase 5 consumes the same signal. Stop citing `perandre/ns-dashboard` in the multi-runner doc.
- `add-tests`'s "213 false-coverage tests" incident (referenced in `tasks/add-tests.md`) is the canonical reminder that scope drift in code-fixing tasks is a real failure mode. Phase 6 (self-review as real review event) is the right place to address recurrence. If it recurs before Phase 6 ships, hotfix `add-tests.md` heuristics.

## First concrete action

Run this from the repo root to verify the credibility leak in 30 seconds, then start Phase 1:

```sh
curl -sS -o /dev/null -w 'canonical: %{http_code}\n' https://frontkom.github.io/night-shift/ \
  && curl -sS -o /dev/null -w 'mirror: %{http_code}\n' https://perandre.github.io/ns/ \
  && grep -n '178\|~71h' index.html
```

You will see `canonical=404`, `mirror=200`, and the hardcoded values at lines 1469 and 1474.

File the GitHub Issue on `frontkom/night-shift` titled `Enable GitHub Pages on frontkom/night-shift (org-admin)` and assign to whoever holds Frontkom org-admin. That issue gates everything downstream. While waiting on admin, open `index.html` and start the em-dash hydration edit — safe to ship the credibility-emergency commit before Pages goes live.
