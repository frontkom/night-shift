# SEO & Metadata

Review page metadata across the site. **One PR with all fixes.**

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: key pages, doc/UI language, test command, build command, default branch, push protocol. If the dispatcher passed `allowed_tasks` and `improve-seo` is not in it, exit silently.

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`), operate inside that app only:
- Read `key pages` from the scoped config (the `apps[]` entry for this app), not the top-level list.
- Only audit and modify files under `<app_path>`.
- Use the app-scoped test and build commands from the scoped config.
- Branch: `nightshift/seo-<app-slug>-YYYY-MM-DD`.
- PR title: `nightshift/seo: <app_path> — metadata sweep`.

Without an `app_path`, behave as before.

## High bar — default is silent
Only open a PR for clear, real SEO issues on genuinely public pages. Do not add metadata just because something could be slightly more descriptive, do not rewrite already-reasonable titles, and do not touch authenticated routes beyond `robots`/`noindex`. **If metadata is broadly in good shape, exit silently.**

## Steps
1. Check for an existing open night-shift SEO PR for this app (or repo when unscoped):
   ```
   gh pr list --search "nightshift/seo in:title" --state open
   ```
   If one exists for the same app, exit silently — do not stack PRs.

2. **Classify each key page as public or authenticated** before auditing.
   A page is **authenticated** (not public-facing) if **any** of the following are true:
   - It lives under a route segment wrapped by auth middleware that redirects unauthenticated users (check `middleware.ts`/`middleware.js` matcher config).
   - The page or its layout calls auth/session helpers (`getServerSession`, `auth()`, `getSession`, `requireAuth`, `useSession` with required, `redirect` on missing session, etc.) and **redirects or blocks** unauthenticated visitors rather than rendering public content.
   - The route sits inside a group or folder whose name strongly implies auth: `(dashboard)`, `(app)`, `(protected)`, `(admin)`, `(account)`, `(settings)`, or similar.
   - The page is not referenced in `sitemap.xml` or `sitemap.ts` **and** has `noindex` or is excluded by `robots.txt`.

   When in doubt, treat the page as authenticated — it is far worse to add social-preview meta to a private page than to miss it on a public one.

3. For each **public** key page (and the root layout under `<app_path>` when scoped), audit:
   - `<title>` — present, unique, descriptive, length sane
   - `<meta name="description">` — present, unique, ~150 chars, in correct language
   - **Open Graph** — `og:title`, `og:description`, `og:image`, `og:type`, `og:url`
   - **Canonical URL** — present and correct
   - **`lang` attribute** on `<html>` matches the project language
   - **JSON-LD** where it makes sense (Organization, Product, Article, BreadcrumbList)
   - **`robots`** meta and `robots.txt` — make sure non-public routes aren't indexable, and public routes aren't blocked
   - **`sitemap.xml`** — exists and references current routes
   - **Do not** add Twitter Card tags (`twitter:card`, `twitter:title`, `twitter:description`, `twitter:image`).

4. For each **authenticated** key page, **do not** add or modify:
   - Open Graph tags, `og:image`, JSON-LD, or structured data.
   - These tags serve social previews and crawlers that will never reach authenticated pages.
   - You may still fix `<title>` and `<meta description>` (these help browser tabs/history) but do not add them if they don't already exist.
   - Ensure authenticated routes have `<meta name="robots" content="noindex">` or are excluded via `robots.txt`.
5. Fix all clear issues in one branch (include app slug when scoped):
   ```
   # scoped:
   git checkout -b nightshift/seo-<app-slug>-YYYY-MM-DD
   # unscoped:
   git checkout -b nightshift/seo-YYYY-MM-DD
   ```
6. Run the scoped **test suite** and the scoped **build command**. Both must pass.
7. Push and open the PR (prefix title with `<app_path> — ` when scoped). The wrapper has already created the standard labels for this repo — just attach them. End the body with the Night Shift footer:
   ```
   gh pr create --title "nightshift/seo: <app_path> — metadata sweep" \
     --label nightshift --label "nightshift:audits" \
     --body "$(cat <<'EOF'
   ## Plain summary
   <1-2 sentences in English (PR review is always in English, regardless of the product's user language). Which public pages now show better titles / link previews / search snippets, and what visitors / search engines see differently. No og:* / JSON-LD jargon here. See bundles/_multi-runner.md → "Body header — Plain summary".>

   ## Summary
   Reviewed SEO metadata across key pages.

   ## Changes
   - <bullet per fix, grouped by page>

   ## Verification
   - <how to confirm in the rendered HTML>

   ---
   _Run by Night Shift • audits/improve-seo_
   EOF
   )"
   ```

   **Do not** modify `docs/NIGHTSHIFT-HISTORY.md` from this branch — the multi-runner wrapper appends the history row on `main` after you return your one-line result.

## Idempotency
- One sweep PR open at a time.
- If everything is already in good shape, exit silently.
