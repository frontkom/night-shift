# Cherry-pick vendor theme update (Shopify)

When the project's `vendor-update-watch` workflow files an issue noting that an upstream Shopify theme (Horizon, Dawn, Skeleton-theme) has a newer version than `.vendor-baseline`, this task downloads the upstream tree, runs the project's `diff_vendor_update.py`, and opens **one PR per logical concern** (perf, a11y, new sections, fixes) rather than a single mega-commit. **One issue → one batch of PRs.**

This task is Shopify-specific. Enable it for a project by selecting it during night-shift bundle setup.

## Read project config first

Read `CLAUDE.md` for **Night Shift Config**: default branch, push protocol. If the dispatcher passed `allowed_tasks` and `shopify-cherry-pick-vendor-update` is not in it, exit silently.

## High bar — default is silent

If there is no open issue with the `vendor-update` label, exit silently. **Zero changes is the correct outcome on most nights** — vendor releases are infrequent.

If `.vendor-baseline` is missing or doesn't reference a known upstream (`horizon`, `dawn`, `skeleton`/`skeleton-theme`), exit silently with a one-line note in the run summary.

## Steps

1. **Find the trigger issue.** Look for the most recent open issue:
   ```
   gh issue list --label "vendor-update" --state open --json number,title,body --limit 5
   ```
   If none, exit silently. If multiple, take the most recent — it supersedes older drafts.

2. **Parse the issue body** for the upstream version. The body (filed by `vendor-update-watch.yml`) contains lines like:
   ```
   Currently on `horizon@3.4.0`. Latest upstream: `horizon@3.5.0` (source: Shopify/horizon).
   ```
   Extract `<theme>`, `<ours>`, `<upstream>`, `<upstream_repo>`. If the issue body doesn't match the expected format, comment on the issue ("Night Shift couldn't parse the version pair from this issue body — leaving for manual cherry-pick") and exit.

3. **Verify our `.vendor-baseline` matches `<ours>`.** If a previous cherry-pick already advanced it past `<ours>`, exit silently — the issue is stale.

4. **Check for an existing open vendor-update PR for the same upstream version:**
   ```
   gh pr list --search "vendor-update <theme> <upstream> in:title" --state open --json number
   ```
   If one exists, exit silently — don't stack PRs.

5. **Download the upstream tree** to `/tmp/<theme>-<upstream>`:
   ```
   gh repo clone <upstream_repo> /tmp/<theme>-<upstream> -- --depth=1 --branch main
   ```
   For Horizon specifically (which doesn't tag releases), main reflects the latest. For Dawn / Skeleton, `--branch v<upstream>` if a release tag exists; else fall back to main.

6. **Run the project's diff helper:**
   ```
   python -m scripts.tasks.diff_vendor_update \
     --vendor-tree /tmp/<theme>-<upstream> \
     --our-tree . \
     --baseline-ref HEAD
   ```
   The output classifies every changed file as `vendor-only-changed`, `ours-only-changed`, `both-changed`, `vendor-new`, or `vendor-deleted`.

7. **Group `vendor-only-changed` and `vendor-new` files by directory concern:**
   - `assets/`, `*.js`, `*.css` → **perf** group
   - `blocks/`, `sections/`, `templates/` → **schema** group
   - `snippets/` → **components** group
   - `locales/` → **i18n** group
   - `config/` → **settings** group
   - root files (`shopify.theme.toml`, `package.json`, etc.) → **meta** group

   `both-changed` files are NEVER auto-cherry-picked — list them in the meta-group PR body as "manual review" with the per-file diff. Our deliberate edits (marked `▼ FRONTKOM-CUSTOM` per CLAUDE.md §3) take priority; if the vendor change is in the same region, the human merges by hand.

8. **For each non-empty group**, create a branch, copy the relevant vendor files, commit, push, open a PR:
   ```
   git checkout -b night-shift/vendor-update-<theme>-<upstream>-<group>-YYYY-MM-DD
   # Copy the group's files from /tmp/<theme>-<upstream>/ to repo root
   git add <files>
   git commit -m "night-shift(vendor-update): <theme> <ours> → <upstream> (<group>)"
   git push -u origin HEAD
   ```
   Then run the project's `theme-check` and `cypress` smoke spec (see CLAUDE.md Night Shift Config for the exact commands). Both must pass before opening the PR. If either fails:
   - Revert: `git checkout main && git branch -D <branch>`
   - Comment on the trigger issue: "Night Shift attempted the `<group>` slice of `<theme>@<upstream>` but verification failed: <one-line reason>. Leaving for manual cherry-pick."
   - Move on to the next group.

9. **Open the PR with the standard footer.** Always use `--body-file`, never inline `--body`. Title format: `night-shift/vendor-update: <theme> <ours> → <upstream> (<group>)` — the `night-shift/<slug>:` convention applies here exactly as it does to every other Night Shift task; the slug is `vendor-update` (from `manifest.yml`). Body:
   ```
   cat > /tmp/night-shift-pr-body.md <<EOF
   ## Plain summary
   <1-2 sentences in English. Which user-facing thing changes (or doesn't): "Horizon's product card now has X feature; perf/a11y unchanged in this slice." Audience: a designer reading the PR list during morning review.>

   ## Summary
   Cherry-pick of upstream <theme> $ours → $upstream, restricted to the `<group>` concern. <N> files changed.

   ## Triage report

   <inline output of diff_vendor_update.py for THIS group only — vendor-changed list>

   ## Files NOT included in this PR

   - `both-changed` files (manual review): <list>
   - Other groups: see sibling PRs from this trigger issue.

   ## What this leaves behind

   - `.vendor-baseline` will only flip to `<theme>@<upstream>` after ALL groups for this issue land. The last group's PR includes the bump.
   - Decision record: open `docs/decisions/NNNN-vendor-update-<theme>-<upstream>.md` capturing what was taken, what was skipped, and why.
   - Trigger issue (#$issue) stays open until all groups are reviewed.

   ---
   <Night Shift footer per repo template>
   EOF

   gh pr create \
     --title "night-shift/vendor-update: $theme $ours → $upstream ($group)" \
     --label "night-shift,vendor-update,$theme,claude-monitor" \
     --body-file /tmp/night-shift-pr-body.md
   ```

10. **After all groups are processed** (success or failure), comment on the trigger issue with the summary:
    ```
    gh issue comment $issue --body "Night Shift cherry-picked $theme $ours → $upstream into <N> PRs grouped by concern: <list of PR URLs>. Manual-review files: <count>. Skipped groups (verification failed): <list with one-line reason>."
    ```

## Why grouped PRs and not one big diff

Vendor updates routinely touch 60+ files. A single PR makes it impossible to review each concern on its own merits — perf changes get rubber-stamped because they're hidden among schema changes. Splitting by directory mirrors the team's mental model when reviewing: someone owns perf-tuning judgment; someone else owns block/schema changes. Each PR is reviewable in isolation.

The merge order matters: meta first (so `.vendor-baseline` doesn't bump prematurely), then schema, then components, then perf, then i18n. Our deliberate edits with `▼ FRONTKOM-CUSTOM` markers sit in `both-changed` files — those never auto-merge, only get listed.

## Cross-references

- `docs/decisions/NNNN-vendor-update-<theme>-<upstream>.md` — write-up per release (what we took / what we skipped / why)
- claude-shopify-boilerplate `CLAUDE.md` §3 "Cherry-picking vendor updates" — the manual-flow this task automates
- claude-shopify-boilerplate `scripts/tasks/diff_vendor_update.py` — the file-classification engine
- The vendor-update-watch.yml workflow that filed the trigger issue
