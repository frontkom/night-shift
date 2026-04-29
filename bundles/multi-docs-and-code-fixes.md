# Multi-repo: Docs + Code fixes (composition)

You are running **two** Night Shift bundles in one session: **docs** first, then **code-fixes**, against all target repositories cloned into this session.

**Before doing anything else**, print a single status line so the user sees immediate output:
`Night Shift docs + code-fixes bundle starting (multi-repo)...`

This is a runtime composition that runs docs and code-fixes in a single session. It exists as a convenience for setups that want to minimise the number of routines. For setups with enough routine slots, `multi-docs.md` and `multi-code-fixes.md` can be used separately instead. The two underlying bundles are unchanged — see `bundles/docs.md` and `bundles/code-fixes.md` for what each does.

## Why docs runs first

Docs tasks edit markdown only and never affect the test suite. Code-fixes tasks require a green test baseline. Running docs first means: even if a code-fixes task fails verification on a particular repo, that repo still gets its docs updates.

## Parse the per-repo allowlist first

Before discovering repos, scan **your own invocation prompt** for a `<night-shift-config>…</night-shift-config>` block and parse the `repos:` map out of it. See `bundles/_multi-runner.md` → **Per-repo task allowlist** for the exact contract. If absent or malformed → no allowlist (all tasks allowed), log `allowlist: none (running all tasks)` in the summary.

This wrapper runs **two** bundles. Fetch `https://raw.githubusercontent.com/frontkom/night-shift/main/manifest.yml` once and collect task ids per bundle dynamically — do **not** hardcode lists here so new tasks flow through automatically. For each repo compute:

- `docs_allowed = allowlist[repo] ∩ <manifest tasks where bundle=docs>`
- `fixes_allowed = allowlist[repo] ∩ <manifest tasks where bundle=code-fixes>`

If **both** are empty, record `not-selected` for that repo and do not dispatch. If only one is empty, the corresponding inner bundle will receive an empty `allowed_tasks` and self-skip, while the other still runs.

## Discover repos
List sibling directories at the top of your working tree. For each candidate, confirm via `git rev-parse --show-toplevel`.

## Per-work-item loop — isolated subagent per (repo, app)

The **docs** bundle contains a mix of `scope: repo` tasks (`document-decisions`, `suggest-improvements`) and `scope: app` tasks (`update-changelog`, `update-user-guide`). The **code-fixes** bundle is entirely `scope: app`. See `bundles/_multi-runner.md` for the full discovery rule.

In a repo with an `apps:` block: one subagent is dispatched per `apps[]` entry. Inside that subagent, `scope: repo` tasks still only run during the **first** (lexicographically first app_path) dispatch — subsequent dispatches skip them to avoid duplicate ADRs / suggestions. Single-app repos (no `apps:` block) dispatch once with `app_path = —` and run every task.

For each discovered target repo, in directory-name order:

1. From the main wrapper, briefly `cd` into the repo to:
   - Look up the repo in the parsed allowlist. If `docs_allowed` AND `fixes_allowed` are both empty, record `not-selected` and continue (no dispatch for this repo).
   - `git status --porcelain` — if dirty, record `dirty-skip` and continue.
   - Check opt-out signals (`.nightshift-skip`, or `Night Shift: skip` in `CLAUDE.md` / `AGENTS.md` / `README.md`). Record `opted-out` and continue if any are present.
   - **Ensure the `night-shift` label exists on the repo** (idempotent — silent if it already exists). Run this once per repo before dispatching subagents:
     ```
     gh label create night-shift --color "0e8a16" --description "Automated by Night Shift" 2>/dev/null || true
     ```
     See `bundles/_multi-runner.md` → "Labels (created at wrapper level, applied at task level)".
   - Parse `## Night Shift Config` in `CLAUDE.md`. If it contains an `apps:` block, build one work-item per `apps[]` entry (with merged `scoped_config`). Otherwise build a single work-item with `app_path = —`.
   - Capture the absolute repo path. `cd` back to the parent.
2. For each work-item, in `app_path` order (lexicographic), dispatch a `Task` subagent with this prompt (substitute `{REPO_PATH}`, `{APP_PATH}`, `{RUN_REPO_SCOPED_TASKS}` — `true` only for the first work-item of this repo, `false` otherwise; always `true` when `app_path = —`):

   ```
   Your working directory is {REPO_PATH}. cd into it now.
   App scope: {APP_PATH}          # "—" means repo-wide, single-app mode
   Scoped config: {SCOPED_CONFIG}
   Docs allowed tasks: {DOCS_ALLOWED}     # YAML list; may be empty
   Code-fixes allowed tasks: {FIXES_ALLOWED}  # YAML list; may be empty
   Run scope:repo tasks: {RUN_REPO_SCOPED_TASKS}  # when false, skip document-decisions, suggest-improvements

   You are running TWO night-shift bundles in sequence: docs, then code-fixes.

   Step 1 — DOCS:
   If DOCS_ALLOWED is empty, skip this step with outcome `silent` (note: not-selected).
   Otherwise, fetch https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/docs.md
   and execute it against this repository, scoped to {APP_PATH} when it is not "—".
   Pass `allowed_tasks: DOCS_ALLOWED` to the inner bundle so each task self-filters.
   When RUN_REPO_SCOPED_TASKS is false, also skip the `document-decisions` and
   `suggest-improvements` tasks — they already ran in another app's subagent for
   this repo. Capture the outcome (ok / silent / failed) as the docs result.

   Step 2 — CODE FIXES (always run, regardless of docs outcome):
   If FIXES_ALLOWED is empty, skip this step with outcome `silent` (note: not-selected).
   Otherwise, fetch https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/code-fixes.md
   and execute it against this repository, scoped to {APP_PATH} when it is not "—".
   Pass `allowed_tasks: FIXES_ALLOWED` to the inner bundle so each task self-filters.
   All code-fixes tasks are scope: app. Capture the outcome as the code-fixes result.

   CLAUDE.md is optional. Honor `## Night Shift Config` if present, otherwise apply
   the defaults from
   https://raw.githubusercontent.com/frontkom/night-shift/main/bundles/_multi-runner.md.

   Return EXACTLY ONE LINE to me in this format (combined status):
       <status> | docs: <ok|silent|failed> | code-fixes: <ok|silent|failed> | <terse note>

   Where the combined status is:
   - `ok`     — at least one of docs / code-fixes did real work successfully
   - `silent` — both docs and code-fixes self-skipped with nothing to do
   - `failed` — at least one returned failed (the other may still have run successfully)
   ```
3. Capture only the one-line result. Do not echo subagent work into your own context.
4. Move on to the next work-item.

If a subagent dispatch itself fails, record `failed | docs: — | code-fixes: — | dispatch error: <reason>` in the summary.

After all work-items for this repo have completed, run the **PR body sweep** in the repo as a wrapper-level safety net for subagents that skipped their per-task post-create ritual. Idempotent — only modifies bodies that contain literal `\n` sequences:

```bash
( cd "$REPO_PATH" && \
  for pr in $(gh pr list --label night-shift --state open --json number --jq '.[].number'); do
    body=$(gh pr view "$pr" --json body -q .body)
    case "$body" in
      *'\n'*)
        printf '%s' "$body" | python3 -c "import sys;sys.stdout.write(sys.stdin.read().replace(chr(92)+chr(110),chr(10)))" > /tmp/night-shift-body-fix.md
        gh pr edit "$pr" --body-file /tmp/night-shift-body-fix.md
        ;;
    esac
  done )
```

## Final report
Print this summary table and stop. The summary table is the primary artifact — it appears in the routines dashboard. The per-repo PR list (`gh pr list --label night-shift`) is the persisted audit trail.

```
Night Shift docs+code-fixes — multi-repo summary

| Repo | App | Status | Docs | Code fixes | Notes |
|------|-----|--------|------|------------|-------|
| ...  | <app_path or —> | ok / silent / not-selected / opted-out / dirty-skip / failed | ok / silent / failed / — | ok / silent / failed / — | <terse> |
```

The `App` column shows `—` for single-app repos and one row per app for monorepos that declare `apps:`.
