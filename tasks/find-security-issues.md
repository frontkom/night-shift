# Security Audit

Scan for OWASP Top 10 patterns. **One PR per issue.**

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: test command, build command, default branch, push protocol. If the dispatcher passed `allowed_tasks` and `find-security-issues` is not in it, exit silently.

**Scoping.** Secret scanning is always repo-wide. The OWASP code review is per-app when the dispatching multi-runner passes an `app_path` (non-empty, not `—`):
- If `app_path` is set, review only code under `<app_path>` for injection / auth / CSRF / XSS patterns.
- Run the repo-wide secret scan pre-step **only** when the multi-runner tells you to (first work-item of a repo). Subsequent app work-items skip the secret scan.
- Use the app-scoped test and build commands from the scoped config.
- Branch and PR title include the app slug: `nightshift/security-<app-slug>-YYYY-MM-DD` and `nightshift/security: <app_path> — <short description>`.

Without an `app_path`, behave as before (whole repo, no app slug).

## High bar — default is silent
Only open a PR for a clearly demonstrable vulnerability with a clearly correct fix. Speculative findings, defense-in-depth wishlist items, and "maybe an attacker could…" patterns do **not** qualify. A false-positive security PR erodes trust and wastes reviewer time. **Zero findings is the correct outcome on most nights.**

## Pre-step — repo-wide secret scan (skip when the runner says so)
Regardless of app scope, once per repo per night, grep the whole repo for accidentally committed secrets: API keys, tokens, private URLs, `NEXT_PUBLIC_*` with sensitive values. If found, file the fix under a plain `nightshift/security-secrets-YYYY-MM-DD` branch (no app slug — it's a repo-wide concern) and return.

## Steps
1. Check for existing open night-shift security PRs to avoid duplicates:
   ```
   gh pr list --search "nightshift/security in:title" --state open
   ```
2. Look for patterns (inside `<app_path>` when scoped; skip the "Exposed secrets" row here — it's handled by the pre-step above):
   - **Auth bypass / broken access control** — routes/handlers that read user IDs from request without authorization checks (IDOR)
   - **Injection** — raw SQL string building, shell exec with user input, unsafe template eval
   - **XSS** — `dangerouslySetInnerHTML`, `innerHTML`, unescaped output in templates
   - **Exposed secrets** — API keys, tokens, private URLs in client bundles, public repos, or `NEXT_PUBLIC_*`
   - **CSRF** — state-changing routes without origin/CSRF protection
   - **Missing rate limiting** on auth, signup, password reset, expensive endpoints
   - **Insecure deserialization, SSRF, open redirects**
3. Pick **one** real, non-speculative issue tonight. Skip anything that requires guessing about intent. When scoped, the issue and its fix must live under `<app_path>`.
4. Create a branch (include the app slug when scoped):
   ```
   # scoped:
   git checkout -b nightshift/security-<app-slug>-YYYY-MM-DD
   # unscoped:
   git checkout -b nightshift/security-YYYY-MM-DD
   ```
5. Fix the issue at the smallest reasonable scope. Add a regression test.
6. Run the scoped **test suite** and the scoped **build command**. Both must pass.
7. Push and open a PR (prefix the title with `<app_path> — ` when scoped). Ensure the standard labels exist first (idempotent), then attach them. End the body with the Night Shift footer:
   ```
   gh label create nightshift --color "0e8a16" --description "Automated by Night Shift" 2>/dev/null || true
   gh label create "nightshift:audits" --color "1d76db" --description "Night Shift audits bundle" 2>/dev/null || true
   gh pr create --title "nightshift/security: <app_path> — <short description>" \
     --label nightshift --label "nightshift:audits" \
     --body "$(cat <<'EOF'
   ## Plain summary
   <1-2 sentences in English (PR review is always in English, regardless of the product's user language). What kind of attack was possible, what data or accounts were at risk, what changes now. No symbol names, no file paths, no CVE IDs in this section. See bundles/_multi-runner.md → "Body header — Plain summary".>

   ## Summary
   <what was vulnerable, in 1-2 sentences>

   ## Risk
   <impact if exploited>

   ## Fix
   <what changed and why this is the right fix>

   ## Verification
   <how the new test demonstrates the fix>

   ---
   _Run by Night Shift • audits/find-security-issues_
   EOF
   )"
   ```

   **Do not** modify `docs/NIGHTSHIFT-HISTORY.md` from this branch — the multi-runner wrapper appends the history row on `main` after you return your one-line result.

## Idempotency
- One issue per night, one PR per issue.
- If a similar PR is already open or merged recently, skip the issue.
- If no real issues are found, exit silently — never fabricate findings.
