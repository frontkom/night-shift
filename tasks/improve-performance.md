# Performance

Review performance across key pages. **One PR with all fixes.**

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: key pages, test command, build command, default branch, push protocol. If the dispatcher passed `allowed_tasks` and `improve-performance` is not in it, exit silently.

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`), operate inside that app only:
- Read `key pages` from the scoped config (the `apps[]` entry for this app), not the top-level list.
- Only audit and modify files under `<app_path>`.
- Use the app-scoped test and build commands from the scoped config.
- Branch: `night-shift/perf-<app-slug>-YYYY-MM-DD`.
- PR title: `night-shift/perf: <app_path> — performance sweep`.

Without an `app_path`, behave as before (top-level key pages, whole repo, no app slug).

## High bar — default is silent
Only open a PR when you can point to a concrete, low-risk win that will clearly help the project. Micro-optimizations, cosmetic refactors dressed up as perf work, and speculative "this might be faster" changes do **not** qualify. **Zero changes is the correct outcome on most nights** — leave bigger or riskier ideas as a note in `docs/SUGGESTIONS.md` instead.

## Steps
1. Check for an existing open night-shift performance PR for this app (or repo when unscoped):
   ```
   gh pr list --search "night-shift/perf in:title" --state open
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
   git checkout -b night-shift/perf-<app-slug>-YYYY-MM-DD
   # unscoped:
   git checkout -b night-shift/perf-YYYY-MM-DD
   ```
   Skip anything that would require a meaningful refactor — leave a note in `docs/SUGGESTIONS.md` (repo-root) instead.
4. Run the scoped **test suite** and the scoped **build command**. Both must pass.
5. Push and open the PR (prefix title with `<app_path> — ` when scoped). The wrapper has already created the standard labels for this repo — just attach them. **Always use `--body-file`, never inline `--body`.** End the body with the Night Shift footer:
   ```
   cat > /tmp/night-shift-pr-body.md <<'EOF'
   ## Plain summary
   <1-2 sentences in English (PR review is always in English, regardless of the product's user language). Which pages feel faster now, by roughly how much (e.g. "~30% faster initial paint on the dashboard"), and who notices (anyone visiting that page on slow connections). No bundle-name jargon. See bundles/_multi-runner.md → "Body header — Plain summary".>

   ## Summary
   Performance pass over key pages.

   ## Changes
   - <bullet per fix, grouped by area>

   ## Expected impact
   - <bundle size delta, render path improvements, etc.>

   ---
   _Run by Night Shift • audits/improve-performance_
   EOF

   PR_URL=$(gh pr create --title "night-shift/perf: <app_path> — performance sweep" \
     --label night-shift \
     --body-file /tmp/night-shift-pr-body.md)
   # Post-create ritual — REQUIRED after every gh pr create. Do NOT return to the wrapper without running every line below. Skipping leaves PR bodies flattened (literal \n on GitHub) or auto-merge unarmed. Spec: bundles/_multi-runner.md.
   gh pr edit "$PR_URL" --add-label night-shift
   BODY=$(gh pr view "$PR_URL" --json body -q .body)
   case "$BODY" in *'\n'*) printf '%s' "$BODY" | python3 -c "import sys;sys.stdout.write(sys.stdin.read().replace(chr(92)+chr(110),chr(10)))" > /tmp/night-shift-body-fix.md && gh pr edit "$PR_URL" --body-file /tmp/night-shift-body-fix.md ;; esac
   gh pr merge "$PR_URL" --auto --squash 2>/dev/null || gh pr merge "$PR_URL" --auto || true
   ```

   **Self-review.** After the post-create ritual above, run the **Self-review + one revision** step from `_multi-runner.md` before returning your one-line result. One review, at most one revision commit, same branch; if the revision breaks tests, revert with `git push --force-with-lease` and keep the original PR.

## Idempotency
- One sweep PR open at a time.
- If nothing low-risk is left to fix, exit silently. Do not force-fit changes.
