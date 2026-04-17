# Accessibility (WCAG 2.1 AA)

Audit key pages for WCAG 2.1 AA violations. **One PR with all fixes.**

## Read project config first
Read `CLAUDE.md` for **Night Shift Config**: key pages, test command, build command, default branch, push protocol. If the dispatcher passed `allowed_tasks` and `improve-accessibility` is not in it, exit silently.

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`), operate inside that app only:
- Read `key pages` from the scoped config (the `apps[]` entry for this app), not the top-level list.
- Only audit and modify files under `<app_path>`.
- Use the app-scoped test and build commands from the scoped config.
- Branch: `nightshift/a11y-<app-slug>-YYYY-MM-DD`.
- PR title: `nightshift/a11y: <app_path> — WCAG 2.1 AA sweep`.

Without an `app_path`, behave as before.

## High bar — default is silent
Only open a PR for violations that are clearly demonstrable from the code and whose fix clearly improves accessibility for real users. Skip hypothetical issues, cosmetic contrast tweaks on already-compliant text, and anything that requires guessing at intent. **If the configured key pages are broadly compliant, exit silently** — a half-empty sweep PR is worse than no PR.

## Steps
1. Check for an existing open night-shift a11y PR for this app (or repo when unscoped):
   ```
   gh pr list --search "nightshift/a11y in:title" --state open
   ```
   If one exists for the same app, exit silently — do not stack PRs.

2. Read the source of each configured **key page** (scoped to `<app_path>` when set) and the components they render.

3. Audit against the **WCAG 2.1 AA success criteria**. Check each category:

   **Perceivable**
   - Images missing meaningful `alt` text (decorative images should have `alt=""`)
   - Video/audio without captions or transcripts
   - Content that relies on color alone to convey meaning
   - Color contrast below 4.5:1 for normal text, 3:1 for large text (18px+ bold or 24px+)
   - Text embedded in images instead of real text
   - Content not reflowable at 320px viewport without horizontal scrolling
   - Text cannot be resized to 200% without loss of content or function

   **Operable**
   - Interactive elements not keyboard reachable or operable (buttons, links, custom widgets)
   - Missing visible focus indicator on focusable elements
   - Focus order that doesn't match visual/logical reading order
   - Keyboard traps (focus enters but can't leave without a mouse)
   - Missing skip navigation link for repeated content blocks
   - Page titles that don't describe the page topic/purpose
   - Link text that is ambiguous out of context ("click here", "read more" without `aria-label`)
   - Touch targets smaller than 24x24 CSS pixels

   **Understandable**
   - Missing or wrong `lang` attribute on `<html>` (or on inline foreign-language spans)
   - Form inputs without associated `<label>` (or `aria-label`/`aria-labelledby`)
   - Missing error identification and suggestion on form validation
   - Inconsistent navigation patterns across pages

   **Robust**
   - Invalid or misused `role` / `aria-*` attributes
   - Custom components missing required ARIA roles, states, and properties
   - Duplicate `id` attributes on the same page
   - Heading hierarchy that skips levels (h1 → h3) or uses headings for styling

4. Fix **all** clear violations. Prioritize by impact — issues that block access entirely (keyboard traps, missing form labels, broken focus management) before cosmetic issues (contrast tweaks on secondary text). Every violation must be real and demonstrable from reading the code, not hypothetical. Fix at the component level so all consumers benefit.

5. **Verify fixes don't introduce regressions:**
   - If the project has a11y tests (e.g. jest-axe, @axe-core/react, Playwright a11y assertions), add tests that would have caught the original violations.
   - Otherwise, add tests that exercise the fixes — at minimum render tests asserting the corrected attributes/elements are present.
   - Read the surrounding code and any existing tests for each component. Make sure fixes don't break existing behavior: conditional rendering, event handlers, CSS class names, prop interfaces.
   - Do not change existing `<title>`, metadata, heading text, or visible copy unless the fix specifically requires it.

6. Collect all fixes in one branch (include app slug when scoped):
   ```
   # scoped:
   git checkout -b nightshift/a11y-<app-slug>-YYYY-MM-DD
   # unscoped:
   git checkout -b nightshift/a11y-YYYY-MM-DD
   ```
7. Run the scoped **test suite** and the scoped **build command**. Both must pass.
8. Push and open the PR (prefix title with `<app_path> — ` when scoped). Ensure the standard labels exist first (idempotent), then attach them. End the body with the Night Shift footer:
   ```
   gh label create nightshift --color "0e8a16" --description "Automated by Night Shift" 2>/dev/null || true
   gh label create "nightshift:code-fixes" --color "1d76db" --description "Night Shift code-fixes bundle" 2>/dev/null || true
   gh pr create --title "nightshift/a11y: <app_path> — WCAG 2.1 AA sweep" \
     --label nightshift --label "nightshift:code-fixes" \
     --body "$(cat <<'EOF'
   ## Summary
   Audited key pages against WCAG 2.1 AA and fixed all violations found.

   ## Changes
   - <bullet per fix, grouped by component/page>

   ## WCAG criteria addressed
   - <list success criteria numbers, e.g. 1.1.1 Non-text Content>

   ## Verification
   - <how to confirm each fix in the rendered page>

   ---
   _Run by Night Shift • code-fixes/improve-accessibility_
   EOF
   )"
   ```

   **Do not** modify `docs/NIGHTSHIFT-HISTORY.md` from this branch — the multi-runner wrapper appends the history row on `main` after you return your one-line result.

## Idempotency
- One sweep PR open at a time.
- If no clear violations remain on the configured key pages, exit silently.
