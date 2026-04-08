# SEO & Metadata

Review page metadata across the site. **One PR with all fixes.**

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: key pages, doc/UI language, test command, build command, default branch, push protocol. If this task is not in the task list, exit.

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`), operate inside that app only:
- Read `key pages` from the scoped config (the `apps[]` entry for this app), not the top-level list.
- Only audit and modify files under `<app_path>`.
- Use the app-scoped test and build commands from the scoped config.
- Branch: `nightshift/seo-<app-slug>-YYYY-MM-DD`.
- PR title: `nightshift/seo: <app_path> — metadata sweep`.

Without an `app_path`, behave as before.

## Steps
1. Check for an existing open night-shift SEO PR for this app (or repo when unscoped):
   ```
   gh pr list --search "nightshift/seo in:title" --state open
   ```
   If one exists for the same app, exit silently — do not stack PRs.
2. For each configured **key page** (and the root layout under `<app_path>` when scoped), audit:
   - `<title>` — present, unique, descriptive, length sane
   - `<meta name="description">` — present, unique, ~150 chars, in correct language
   - **Open Graph** — `og:title`, `og:description`, `og:image`, `og:type`, `og:url`
   - **Twitter Card** — `twitter:card`, `twitter:title`, `twitter:description`, `twitter:image`
   - **Canonical URL** — present and correct
   - **`lang` attribute** on `<html>` matches the project language
   - **JSON-LD / microdata** where it makes sense (Organization, Product, Article, BreadcrumbList)
   - **`robots`** meta and `robots.txt` — make sure non-public routes aren't indexable, and public routes aren't blocked
   - **`sitemap.xml`** — exists and references current routes
3. Fix all clear issues in one branch (include app slug when scoped):
   ```
   # scoped:
   git checkout -b nightshift/seo-<app-slug>-YYYY-MM-DD
   # unscoped:
   git checkout -b nightshift/seo-YYYY-MM-DD
   ```
4. Run the scoped **test suite** and the scoped **build command**. Both must pass.
5. Push and open the PR (prefix title with `<app_path> — ` when scoped):
   ```
   gh pr create --title "nightshift/seo: <app_path> — metadata sweep" \
     --body "$(cat <<'EOF'
   ## Summary
   Reviewed SEO metadata across key pages.

   ## Changes
   - <bullet per fix, grouped by page>

   ## Verification
   - <how to confirm in the rendered HTML>
   EOF
   )"
   ```

## Idempotency
- One sweep PR open at a time.
- If everything is already in good shape, exit silently.
