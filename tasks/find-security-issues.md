# Task 08 — Security Audit

Scan for OWASP Top 10 patterns. **One PR per issue.**

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: test command, build command, default branch, push protocol. If task 8 is not in the task list, exit.

## Steps
1. Check for existing open night-shift security PRs to avoid duplicates:
   ```
   gh pr list --search "nightshift/security in:title" --state open
   ```
2. Look for patterns:
   - **Auth bypass / broken access control** — routes/handlers that read user IDs from request without authorization checks (IDOR)
   - **Injection** — raw SQL string building, shell exec with user input, unsafe template eval
   - **XSS** — `dangerouslySetInnerHTML`, `innerHTML`, unescaped output in templates
   - **Exposed secrets** — API keys, tokens, private URLs in client bundles, public repos, or `NEXT_PUBLIC_*`
   - **CSRF** — state-changing routes without origin/CSRF protection
   - **Missing rate limiting** on auth, signup, password reset, expensive endpoints
   - **Insecure deserialization, SSRF, open redirects**
3. Pick **one** real, non-speculative issue tonight. Skip anything that requires guessing about intent.
4. Create a branch:
   ```
   git checkout -b nightshift/security-YYYY-MM-DD
   ```
5. Fix the issue at the smallest reasonable scope. Add a regression test.
6. Run the **full test suite** and the **build command**. Both must pass.
7. Push and open a PR:
   ```
   gh pr create --title "nightshift/security: <short description>" \
     --body "$(cat <<'EOF'
   ## Summary
   <what was vulnerable, in 1-2 sentences>

   ## Risk
   <impact if exploited>

   ## Fix
   <what changed and why this is the right fix>

   ## Verification
   <how the new test demonstrates the fix>
   EOF
   )"
   ```

## Idempotency
- One issue per night, one PR per issue.
- If a similar PR is already open or merged recently, skip the issue.
- If no real issues are found, exit silently — never fabricate findings.
