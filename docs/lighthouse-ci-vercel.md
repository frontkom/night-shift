# Lighthouse CI on Vercel preview deploys

Step-by-step setup for adding Lighthouse CI (LHCI) on top of Vercel preview deploys, running on every preview deploy and posting scores back to the PR. Works with any framework Vercel supports — Next.js, Astro, Remix, Nuxt, plain static, etc. The trigger is Vercel's `deployment_status` GitHub event, which is platform-level, not framework-level. Pilot reference: `frontkom/merkur-frontend` PR #94 (Next.js).

The setup avoids the five mistakes that typically bite first-time LHCI users — see **Gotchas** below.

## What you get

- One Lighthouse run per Vercel preview deploy (mobile profile, median of 3 runs).
- Scores commented back on the PR.
- 14-day artifact retention with the full HTML reports.
- A list of "key pages" that doubles as the audit target list for Night Shift's `improve-performance` task.

## What you don't get out of the box

- PR-blocking thresholds. Assertions are `warn` for the first week — see **Tightening** below.
- Performance budgets (`budget.json`). Add later, once a baseline exists.
- Authenticated-page audits. Public pages only.

## Setup

Three files. Copy-paste, edit the page list, push.

### 1. `.github/workflows/lighthouseci.yml`

```yaml
name: Lighthouse CI

# Trigger on Vercel preview deployment success — not on `pull_request`.
# Running on PR open would race the Vercel build and frequently hit a
# 404 / stale build (gotcha #1 below). `deployment_status` fires
# reliably after Vercel publishes its build state to GitHub.
on:
  deployment_status:

jobs:
  lighthouse:
    name: Lighthouse — Vercel preview
    runs-on: ubuntu-latest

    # Filter to successful Vercel preview deployments only.
    # Production deployments skip — perf baseline lives on PR-level previews.
    if: >-
      ${{ github.event.deployment_status.state == 'success'
          && github.event.deployment.environment != 'Production' }}

    steps:
      - name: Checkout the deployed commit
        uses: actions/checkout@v4
        with:
          ref: ${{ github.event.deployment.sha }}

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install Lighthouse CI
        run: npm install -g @lhci/cli@0.14.x

      - name: Run Lighthouse CI against the Vercel preview
        env:
          # The Vercel preview URL Vercel posted alongside the deployment
          # event. The .lighthouserc.cjs config reads this and prefixes
          # every page in its `urls` list with it.
          LHCI_BASE_URL: ${{ github.event.deployment_status.target_url }}
          # Required for the PR comment. Without it, the workflow still
          # runs and uploads artifacts — just no comment.
          LHCI_GITHUB_APP_TOKEN: ${{ secrets.LHCI_GITHUB_APP_TOKEN }}
        run: lhci autorun

      - name: Upload report artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: lighthouseci-${{ github.event.deployment.sha }}
          path: .lighthouseci/
          retention-days: 14
```

### 2. `.lighthouserc.cjs`

JS module so the dynamic Vercel preview URL can be injected at runtime via `LHCI_BASE_URL`. Edit the `pages` array to match your site.

```js
const baseUrl = process.env.LHCI_BASE_URL || 'http://localhost:3000'

// Edit this list to match your site. These should be the pages where
// performance matters most (highest traffic, slowest, most critical).
// Keep them in sync with any "Key pages" list you maintain elsewhere
// (e.g. CLAUDE.md for Night Shift).
const pages = ['/', '/blog', '/products', '/search']

module.exports = {
  ci: {
    collect: {
      url: pages.map((path) => `${baseUrl}${path}`),
      numberOfRuns: 3,        // median of 3 — flattens GH-runner variance
      settings: {
        formFactor: 'mobile', // most real-world traffic is mobile
        skipAudits: [
          'uses-http2',       // Vercel/HTTPS handles HTTP/2 — no signal
        ],
      },
    },
    assert: {
      // No preset for the pilot week. `lighthouse:no-pwa` inherits ~10
      // audit-level `error` assertions that fail before you've had a
      // chance to baseline. Category-level signal only until stable;
      // tighten + add a preset once it is.
      assertions: {
        'categories:performance':    ['warn', { minScore: 0.7 }],
        'categories:accessibility':  ['warn', { minScore: 0.9 }],
        'categories:best-practices': ['warn', { minScore: 0.9 }],
        'categories:seo':            ['warn', { minScore: 0.9 }],
      },
    },
    upload: {
      // Free Lighthouse-hosted ephemeral storage. Each run gets a
      // permalink the PR comment links to.
      target: 'temporary-public-storage',
    },
  },
}
```

### 3. (Optional) Install the Lighthouse CI GitHub App for PR comments

Without this, the workflow still runs and uploads HTML reports as artifacts — but it won't post a comment with scores.

1. Install [Lighthouse CI](https://github.com/apps/lighthouse-ci) on your repo (org admin or repo admin).
2. Copy the token shown after install.
3. Repo → Settings → Secrets and variables → Actions → New secret: `LHCI_GITHUB_APP_TOKEN`.

That's it.

## Gotchas (and why this setup avoids them)

| # | Gotcha | Mitigation in this setup |
|---|---|---|
| 1 | `pull_request` trigger races Vercel's preview build → Lighthouse hits 404 / stale build | `on: deployment_status` + filter `state == 'success'` |
| 2 | GitHub runners introduce ±10pt Performance variance | `numberOfRuns: 3` + implicit median selection |
| 3 | Default config audits PWA → drags overall score on a non-PWA site | Don't use `lighthouse:no-pwa` preset on day one — start with category-level `warn` only, add the preset after baseline |
| 4 | Default audits only `/` → misses listing pages where the perf budget lives | `urls` array of explicit key pages |
| 5 | Auth/draft-mode pages can't be audited without cookies | Public pages only in the urls list |

## Tightening after the pilot week

After ~5 days of green baseline:

1. Switch any of the four category assertions from `warn` to `error` if you want hard PR gates.
2. Optionally add `preset: 'lighthouse:no-pwa'` for stricter audit-level checks (the preset adds ~10 audit-level `error` assertions; review which ones make sense).
3. Make the `Lighthouse CI` job a required status check on `develop` / `main` branch protection.
4. Optionally add a `budget.json` for bundle-size limits.

## Local debugging

```bash
LHCI_BASE_URL=https://your-preview.vercel.app npx lhci autorun
```

Drop the env var to point at `localhost:3000` instead — useful for sanity-checking the config before pushing.

## How this connects to Night Shift

Night Shift's `improve-performance` audit task (PR #2 in this repo, in review) runs Lighthouse from inside the audit task itself, against production URLs. That works without any per-repo CI setup, but each nightly run pays the Lighthouse runtime cost from scratch.

The setup in this doc gives you something complementary: per-PR Lighthouse signal on every preview deploy, with a 14-day artifact trail. The two approaches can coexist — and the `pages` list in `.lighthouserc.cjs` is the same list `improve-performance` would target if pointed at this repo.
