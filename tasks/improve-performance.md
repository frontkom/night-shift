# Task 11 — Performance

Review performance across key pages. **One PR with all fixes.**

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: key pages, test command, build command, default branch, push protocol. If task 11 is not in the task list, exit.

## Steps
1. Check for an existing open night-shift performance PR:
   ```
   gh pr list --search "nightshift/perf in:title" --state open
   ```
   If one exists, exit silently — do not stack PRs.
2. Audit:
   - **Bundle size** — run the project's bundle analyzer if available, or inspect built output. Look for unexpectedly large modules and accidental client-side imports of server-only code.
   - **Images** — using next/image (or framework equivalent), correct sizes, modern formats, lazy loading on below-the-fold imagery.
   - **Fonts** — preloaded, `font-display: swap`, no FOIT.
   - **Render-blocking resources** — synchronous scripts, blocking CSS, large inline blobs.
   - **Client/server boundary** — components marked client-only that could be server, large data fetched on the client that could be fetched on the server.
   - **Database / API calls** — N+1 patterns, missing indexes implied by query shape, missing caching where appropriate.
   - **Lighthouse-style checks** for each configured **key page** by reading the source (no live browser needed).
3. Fix all clear, low-risk issues in one branch:
   ```
   git checkout -b nightshift/perf-YYYY-MM-DD
   ```
   Skip anything that would require a meaningful refactor — leave a note in `docs/SUGGESTIONS.md` instead.
4. Run the **full test suite** and the **build command**. Both must pass.
5. Push and open the PR:
   ```
   gh pr create --title "nightshift/perf: performance sweep" \
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
