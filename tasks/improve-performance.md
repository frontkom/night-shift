# Performance

Review performance across key pages. **One PR with all fixes.**

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: key pages, test command, build command, default branch, push protocol. If this task is not in the task list, exit.

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`), operate inside that app only:
- Read `key pages` from the scoped config (the `apps[]` entry for this app), not the top-level list.
- Only audit and modify files under `<app_path>`.
- Use the app-scoped test and build commands from the scoped config.
- Branch: `nightshift/perf-<app-slug>-YYYY-MM-DD`.
- PR title: `nightshift/perf: <app_path> — performance sweep`.

Without an `app_path`, behave as before (top-level key pages, whole repo, no app slug).

## Steps
1. Check for an existing open night-shift performance PR for this app (or repo when unscoped):
   ```
   gh pr list --search "nightshift/perf in:title" --state open
   ```
   If one exists for the same app, exit silently — do not stack PRs.
2. Audit:
   - **Bundle size** — run the project's bundle analyzer if available, or inspect built output. Look for unexpectedly large modules and accidental client-side imports of server-only code.
   - **Images** — using next/image (or framework equivalent), correct sizes, modern formats, lazy loading on below-the-fold imagery.
   - **Fonts** — preloaded, `font-display: swap`, no FOIT.
   - **Render-blocking resources** — synchronous scripts, blocking CSS, large inline blobs.
   - **Client/server boundary** — components marked client-only that could be server, large data fetched on the client that could be fetched on the server.
   - **Database / API calls** — N+1 patterns, missing indexes implied by query shape, missing caching where appropriate.
   - **Lighthouse-style checks** for each configured **key page** by reading the source (no live browser needed).
3. Fix all clear, low-risk issues in one branch (include app slug when scoped):
   ```
   # scoped:
   git checkout -b nightshift/perf-<app-slug>-YYYY-MM-DD
   # unscoped:
   git checkout -b nightshift/perf-YYYY-MM-DD
   ```
   Skip anything that would require a meaningful refactor — leave a note in `docs/SUGGESTIONS.md` (repo-root) instead.
4. Run the scoped **test suite** and the scoped **build command**. Both must pass.
5. Push and open the PR (prefix title with `<app_path> — ` when scoped):
   ```
   gh pr create --title "nightshift/perf: <app_path> — performance sweep" \
     --body "$(cat <<'EOF'
   ## Summary
   Performance pass over key pages.

   ## Changes
   - <bullet per fix, grouped by area>

   ## Expected impact
   - <bundle size delta, render path improvements, etc.>
   EOF
   )"
   ```

## Idempotency
- One sweep PR open at a time.
- If nothing low-risk is left to fix, exit silently. Do not force-fit changes.
