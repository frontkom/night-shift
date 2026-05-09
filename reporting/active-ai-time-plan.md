# Plan: Per-project total of "active AI time"

## Context

Can Night Shift produce an *exact* number for how much it has worked, totalled per project per night? Today the answer is "no, not exactly, and not for past nights" — but the gap is small. This plan instruments runs going forward so the number becomes precise and durable, and surfaces it in a visual dashboard.

**Why "exact" isn't possible today:**

- `.github/workflows/night-shift.yml:70` invokes `claude -p` *without* `--output-format json`, so the rich per-run metrics Claude Code already emits — `duration_api_ms` (the time the model was actively producing tokens), `total_cost_usd`, and full `usage` (input / output / cache tokens) — are discarded. We only keep wall-clock seconds from `date +%s` (`night-shift.yml:67,131`).
- The `nightshift-report` event (schema at `reporting/schema.json`) currently has no field for `usage` or `duration_api_ms`, only `duration_seconds`.
- GitHub Actions artifacts expire at 90 days, and the optional `NIGHTSHIFT_REPORT_URL` webhook (`night-shift.yml:233-246`) has no receiver pointed at it.
- Routine-backed runs (via `RemoteTrigger`) emit nothing capturable from outside the session — they run on the Claude Max plan with no per-routine billing endpoint. Wall-clock is the best we can get for that path.

So: **GH-Actions-backed repos can have exact API time. Routine-backed repos can only have wall-clock approximation.** The plan accepts this asymmetry rather than forcing all repos to one backend.

## Recommended approach

Three small pieces, each independently useful.

### 1. Capture richer metrics on every run

**File: `.github/workflows/night-shift.yml`**

Change the `claude -p ...` invocation around line 70-128 to add `--output-format json`, then parse with `jq`:

```bash
RAW=$(claude -p "..." --output-format json --model "${{ inputs.model }}" \
  --allowedTools "Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch" \
  --max-turns "${{ inputs.max-turns }}")

echo "$RAW" > /tmp/claude-output.json
OUTPUT=$(jq -r '.result' /tmp/claude-output.json)        # the markdown summary
DURATION_API_MS=$(jq -r '.duration_api_ms' /tmp/claude-output.json)
DURATION_MS=$(jq -r '.duration_ms' /tmp/claude-output.json)
COST_USD=$(jq -r '.total_cost_usd' /tmp/claude-output.json)
USAGE_JSON=$(jq -c '.usage // {}' /tmp/claude-output.json)
```

Plumb those through `$GITHUB_OUTPUT` alongside the existing `duration` output and into the event JSON.

**File: `reporting/schema.json`**

Add (non-breaking, new optional fields):

```jsonc
"duration_api_ms":   { "type": "integer", "minimum": 0 },
"duration_ms":       { "type": "integer", "minimum": 0 },
"total_cost_usd":    { "type": "number",  "minimum": 0 },
"usage": {
  "type": "object",
  "properties": {
    "input_tokens":                { "type": "integer" },
    "output_tokens":               { "type": "integer" },
    "cache_creation_input_tokens": { "type": "integer" },
    "cache_read_input_tokens":     { "type": "integer" }
  }
}
```

Add `"backend"` enum value `"routine"` so routine-backed runs can post events too (currently locked to `"github-actions"` at `schema.json:25`).

**Routine backend instrumentation:**

Update the multi-runner / wrapper prompts so the routine, as its final step, appends a JSONL event to the logs repo via `gh api`. Routines can't self-report token counts, so they emit `duration_seconds` (wall-clock) and leave `duration_api_ms` / `usage` absent. The dashboard will mark these as "approximate".

### 2. Persist events durably

Stand up a dedicated **private** `frontkom/night-shift-logs` repo with one JSONL file per month (`logs/2026-05.jsonl`). Append-only; each line is a schema-conformant event.

- **GH-Actions backend** — have the workflow itself append directly via `gh api` contents API (read JSONL → append line → put with sha) using a fine-scoped PAT stored as `NIGHTSHIFT_LOGS_TOKEN`. No hosted webhook receiver needed.
- **Routine backend** — same pattern: the routine commits one JSONL line at the end of its run, using the same PAT.

**Why private even though events contain no credentials:** the events still carry sensitive metadata — repo names of every targeted project (including any private repos, which leaks their existence and naming), bundle outcomes (e.g. "audits failed on repo X" is a soft attention signal), and aggregate token/cost volume. The framework repo (`frontkom/night-shift`) stays open source; only the *operational telemetry* moves behind an auth boundary.

### 3. Dashboard

The dashboard reads the same JSONL feed, so it inherits the same privacy boundary — it must not be a public GitHub Pages site.

Recommended host: **Vercel + GitHub OAuth** (or Clerk). A minimal Next.js app that:

- On the server, uses a GitHub App / PAT to fetch `frontkom/night-shift-logs/logs/*.jsonl` from the private repo.
- Gates access to the page itself (only the maintainer / a configured allowlist).
- Renders with Chart.js or Recharts:
  - **Headline number** per project: cumulative active AI time (sum of `duration_api_ms`), with a wall-clock fallback line clearly labelled "approximate (routine backend)".
  - **Time series** per project: stacked area, one band per bundle (plans / docs / code-fixes / audits).
  - **Token + cost** breakdown (only for GH-Actions runs, where data exists).
  - **Cadence**: nights with activity vs. silent nights.

Cheaper fallback if you don't want to stand up a Next.js app yet: a single `index.html` served from a private S3 bucket behind Cloudflare Access, fetching the JSONL via a worker that injects the GitHub token. Same data shape, less framework.

**If you ever want a public showcase**, the path is opt-in only: log a whitelisted set of repos by name (e.g. `frontkom/night-shift` itself, sandbox repos) and aggregate everything else under anonymised `private/*` buckets in a separate public-safe feed.

## Critical files

| File | Change |
|---|---|
| `.github/workflows/night-shift.yml` | Switch to `--output-format json`; extract `duration_api_ms`, cost, usage; pass through to event JSON; append to logs repo. |
| `github-actions/caller-template.yml` | Mirror the same change so downstream callers inherit it. |
| `reporting/schema.json` | Add optional `duration_api_ms`, `duration_ms`, `total_cost_usd`, `usage`; widen `backend` enum to include `"routine"`. |
| `reporting/README.md` | Document the new fields and the logs-repo location. |
| `bundles/_multi-runner.md` (and any wrapper prompts) | Add a final step that appends a JSONL event to the logs repo. |
| `skills/night-shift/SKILL.md` | Bump `NIGHT_SHIFT_VERSION` (frontmatter + HTML comment) per `CLAUDE.md` workflow rule. |
| Dashboard app (new, separate Vercel project) | Auth-gated Next.js page reading the JSONL feed via a server-side GitHub token. Not in this repo. |
| `frontkom/night-shift-logs` (new **private** repo) | Append-only JSONL store. README explains the schema. Private because events carry repo names + activity metadata. |

## What about historical data

A partial backfill is possible from existing artifacts:

```bash
gh run list --workflow night-shift.yml --status completed --json databaseId,createdAt --limit 200 \
  | jq -r '.[].databaseId' \
  | xargs -I{} gh run download {} -n nightshift-report -D /tmp/nsr/{}
```

But: artifacts older than 90 days are gone, and `duration_api_ms` was never captured, so backfill yields only wall-clock + PR counts. Recommend skipping backfill and starting clean from the instrumentation date — the dashboard's "total" is then trustworthy from day one.

## Verification

1. **Workflow change:** trigger manually on the sandbox repo (`gh workflow run night-shift.yml -R <sandbox>`); confirm the produced `event.json` artifact has `duration_api_ms`, `total_cost_usd`, and `usage` populated and validates against the updated schema.
2. **End-to-end:** confirm a new line appended to `frontkom/night-shift-logs/logs/<YYYY-MM>.jsonl` with the same data.
3. **Routine path:** trigger one routine-backed run (existing `night-shift-test` skill); confirm the routine commits a JSONL line with `backend: "routine"` and `duration_seconds`.
4. **Dashboard:** open the deployed Vercel URL (auth-gated); confirm per-project totals render and that routine-backed bars are labelled approximate.
5. **Schema check:** `npx ajv-cli validate -s reporting/schema.json -d 'logs/*.jsonl'` passes.

## Scope estimate

- Workflow + schema changes: ~1 hour.
- Logs repo + commit-append step: ~1 hour.
- Routine prompt addendum + version bump: ~30 minutes.
- Dashboard (single-page Chart.js): ~2-3 hours including styling.
- Total: ~half a day of focused work; ships incrementally — the workflow change can land first and produce JSON-formatted artifacts before any dashboard exists.
