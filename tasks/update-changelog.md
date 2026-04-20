# Changelog

Update the project's changelog if there are new user-facing changes since the last entry.

## Read project config first
Read `CLAUDE.md` for the **Night Shift Config** section: doc language, changelog format, push protocol. If the dispatcher passed `allowed_tasks` and `update-changelog` is not in it, exit silently.

**Scoping.** If the dispatching multi-runner passes an `app_path` (non-empty, not `—`):
- Prefer a per-app changelog at `<app_path>/CHANGELOG.md`. Create it if missing.
- If the app has no changelog but the repo root does (`CHANGELOG.md` or `docs/CHANGELOG.md`), write to the repo-root changelog **and** prefix each entry with the app name so readers know which app changed (`- (web) Added …`).
- Scope the `git log` to paths under `<app_path>`:
  `git log --since=<last-entry-date> --no-merges --oneline -- <app_path>`
- Commit message names the app: `nightshift(changelog): <app_path> — update for recent user-facing changes`.

Without an `app_path`, behave as before.

## High bar — default is silent
The changelog is read by **end users and stakeholders**, not by engineers. An entry only earns its line when a real user of the product would notice the change and care about it. Internal cleanup, invisible plumbing, and "could have caused" defensive fixes do **not** belong in the changelog — they live in git history and PR descriptions, not in user-facing release notes.

If a week's commits are mostly refactors, dependency bumps, internal Night Shift fixes, or invisible polish, **exit silently**. A short, sharp changelog beats a padded one — every weak entry trains readers to skip the file.

### Hard exclusions — never write a changelog entry for these
- **Pure accessibility plumbing** (e.g. adding `role="alert"`, `aria-hidden`, or `aria-label` to existing visible UI). The user can't see the change. *Exception:* a brand-new accessibility feature a user actually interacts with (high-contrast theme, full keyboard navigation flow, screen-reader-optimised layout) does belong.
- **Hydration / SSR / rendering fixes phrased "could cause flickering / could give a flash"** — if you can't point to a user-visible symptom that real users were reporting, it's an internal fix.
- **Bug fixes whose user impact is "you might never have noticed"** — the cron-reminder over-sending bug *is* user-facing because users received excess emails; a race condition that's only theoretical is *not*.
- **Refactors, renames, dependency bumps, lint fixes, type fixes, test additions, CI changes, build-tooling changes.**
- **Anything sourced from a `nightshift/docs:`, `nightshift/tests:`, `nightshift/perf:`, `nightshift/seo:`, or `nightshift/i18n:` PR.** These are by definition internal maintenance — see the "Source-PR scrutiny" rule below.
- **The same fix applied to multiple apps written as separate per-app entries.** One entry, mention both apps inline.

### Source-PR scrutiny
For each candidate commit, look up the PR it came from (via `gh pr view <#>` if the commit references one). When the source PR title starts with `nightshift/`, apply **extra** scrutiny — Night Shift opens many small internal PRs (a11y sweeps, perf passes, test additions, doc refreshes) that pass the green-CI bar but rarely produce true user-visible value. **Default to skipping `nightshift/...`-sourced commits unless the change is plainly user-visible** (e.g. a `nightshift/bug:` PR that fixed a bug a user would have noticed, or a `nightshift/plan:` PR that shipped a real feature).

### The "would a user write home about this?" test
Read each draft entry aloud as if announcing it to a customer. If your honest reaction is "they won't care" or "they won't know what this means without the codebase open" — drop it. Better one excellent line than three forgettable ones.

## Steps
1. Find the changelog file: `<app_path>/CHANGELOG.md` when scoped, else the repo-root `CHANGELOG.md` / `docs/CHANGELOG.md` (or as configured).
2. Determine the last entry's date or commit reference.
3. Run `git log --since=<last-entry-date> --no-merges --oneline` (scoped to `<app_path>` when set) and inspect commits since then.
4. **First pass — filter** by the hard exclusions and the source-PR scrutiny rule above. Drop everything that fails.
5. **Second pass — would-a-user-write-home test.** For each survivor, draft a one-line entry in the user's language. If the draft fails the test, drop it.
6. **Third pass — de-dup across apps.** If the same underlying change landed in multiple apps, write **one** entry that names both apps inline (e.g. "(Bedrift + Intranett)") instead of one entry per app. The diff feed will list both PRs but the user only needs one bullet.
7. If zero entries survive all three passes, exit silently. **Most weeks should produce ≤ 3 entries; many weeks should produce zero.** That is the correct outcome — do not pad to look productive.
8. Write the surviving entries in the project's configured changelog format and language. Match the tone and structure of existing entries exactly.

## Branch, commit, and open the PR
This task runs in **pull-request mode** (per `manifest.yml`). Create a feature branch, commit your changes there, push, and open a PR with the standardized title format. Ensure labels exist (idempotent), then attach them. End the PR body with the Night Shift footer.

```
# Create the branch (include app slug when scoped):
# scoped:
git checkout -b nightshift/changelog-<app-slug>-YYYY-MM-DD
# unscoped:
git checkout -b nightshift/changelog-YYYY-MM-DD

git add -A
# scoped commit:
git commit -m "nightshift(changelog): <app_path> — update for recent user-facing changes"
# unscoped commit:
git commit -m "nightshift(changelog): update for recent user-facing changes"

git push -u origin HEAD

# Wrapper has already created the standard labels for this repo — just attach them.

cat > /tmp/nightshift-pr-body.md <<'EOF'
## Summary
- <bullet per new entry>

## Source commits
- <list of commits used to derive entries>

---
_Run by Night Shift • docs/update-changelog_
EOF

# scoped PR title:
gh pr create --title "nightshift/changelog: <app_path> — update for recent user-facing changes" \
  --label nightshift --label "nightshift:docs" \
  --body-file /tmp/nightshift-pr-body.md
# unscoped PR title:
# gh pr create --title "nightshift/changelog: update for recent user-facing changes" \
#   --label nightshift --label "nightshift:docs" \
#   --body-file /tmp/nightshift-pr-body.md
```

**Always use `--body-file`, never inline `--body`.** See `bundles/_multi-runner.md` → "PR body formatting".

**Do not** modify `docs/NIGHTSHIFT-HISTORY.md` from this branch — the multi-runner wrapper appends the history row on `main` after you return your one-line result.

## Idempotency
- Never duplicate an entry. If the latest commits are already represented, exit.
- Overwrite drafts only if clearly marked as such — never rewrite published entries.
- Zero new entries is a valid, common outcome. Exit silently rather than open a PR with weak entries.
