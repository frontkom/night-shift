# Night Shift — Run Reporting

Every Night Shift run emits a structured JSON event so results from all
repos can be collected in one place.

## Event schema

See [`schema.json`](schema.json) for the full JSON Schema.

A minimal example:

```json
{
  "repo": "perandre/my-app",
  "timestamp": "2026-04-11T03:15:00Z",
  "run_url": "https://github.com/perandre/my-app/actions/runs/123456",
  "backend": "github-actions",
  "bundles": {
    "plans":      { "status": "ok",      "prs": ["https://github.com/perandre/my-app/pull/42"], "commits": 3 },
    "docs":       { "status": "silent",  "prs": [], "commits": 0 },
    "code-fixes": { "status": "skipped", "prs": [], "commits": 0 },
    "audits":     { "status": "failed",  "prs": [], "commits": 0 }
  },
  "duration_seconds": 340,
  "model": "claude-opus-4-7"
}
```

### Bundle statuses

| Status    | Meaning |
|-----------|---------|
| `ok`      | Bundle ran and produced changes (commits / PRs). |
| `silent`  | Bundle ran but found nothing to do. |
| `skipped` | Bundle was not applicable to this run's task list. |
| `failed`  | Bundle encountered an error. |
| `unknown` | Output could not be parsed — check the run logs. |

## How runs report their results

The reusable GitHub Actions workflow (`.github/workflows/night-shift.yml`)
performs two reporting actions after every run:

1. **Artifact** — The JSON event is saved as a GitHub Actions artifact
   named `nightshift-report`. This is always available, even if no
   external endpoint is configured.

2. **POST to endpoint** — If the `NIGHTSHIFT_REPORT_URL` secret is set,
   the event is POSTed to that URL with `Content-Type: application/json`.
   Failures are logged but never fail the workflow.

## Setting up centralized collection

### Option A: JSONL in a log repo

Create a private repo (e.g. `perandre/nightshift-logs`) with a simple
receiver — a GitHub Actions workflow triggered by `repository_dispatch`,
or a lightweight server — that appends each incoming event as one line
to a `runs.jsonl` file.

### Option B: Webhook endpoint

Point `NIGHTSHIFT_REPORT_URL` at any HTTP endpoint that accepts POST:

- A Vercel serverless function that writes to a database
- A Google Apps Script that appends to a Google Sheet
- A simple Express server writing to a JSONL file

### Configuring the secret

In each repo that calls the Night Shift workflow, add the
`NIGHTSHIFT_REPORT_URL` secret:

```
gh secret set NIGHTSHIFT_REPORT_URL --body "https://your-endpoint.example.com/night-shift"
```

Then pass it in your caller workflow:

```yaml
jobs:
  nightly:
    uses: frontkom/night-shift/.github/workflows/night-shift.yml@main
    with:
      tasks: "build-planned-features,update-changelog"
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      NIGHTSHIFT_REPORT_URL: ${{ secrets.NIGHTSHIFT_REPORT_URL }}
```

The secret is optional. If omitted, reporting still writes the artifact.

## Wall dashboard

There's a tiny static dashboard at `dashboard/index.html` (deployed to
GitHub Pages alongside the framework site) that shows two numbers per
project — hours worked last night, hours worked in total. It reads
`dashboard/runs.jsonl` (one event per line) from the same repo.

To feed the dashboard from your nightly runs, set two optional caller
secrets:

```
NIGHTSHIFT_DASHBOARD_REPO   = "owner/dashboard-host"   # e.g. frontkom/night-shift
NIGHTSHIFT_DASHBOARD_TOKEN  = <PAT with contents:write on that repo>
```

…and pass them through in your caller workflow (see
`github-actions/caller-template.yml`). The reusable workflow then
appends one JSONL line per run, with conflict-retry, so multiple repos
can write concurrently.

"Hours worked" is wall-clock from env start to idle (`duration_seconds`
in the event), which is what the workflow already records — close
enough that drift of a few minutes per run is not a concern.
