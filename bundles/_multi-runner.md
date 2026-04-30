# Multi-repo runner — shared protocol

This file documents the loop semantics used by the `multi-*.md` wrappers. It is not fetched by routines directly — it's reference reading for the wrappers and for humans editing them.

## Per-repo task allowlist (the `<night-shift-config>` block)

The skill stores the per-repo task selection **inside the routine prompt itself**, as a YAML block between explicit delimiters. The wrapper parses this block out of its own invocation prompt on every run and uses it to filter which tasks it dispatches per repo.

**Format** (exact delimiters, no variations):

```
<night-shift-config>
repos:
  https://github.com/owner/repo-a: [build-planned-features, update-changelog, add-tests]
  https://github.com/owner/repo-b: [find-bugs, improve-seo]
</night-shift-config>
```

- Keys are full `https://github.com/owner/repo` URLs (no `.git`, matching how they appear in the routine's `sources[]`). For a monorepo with `apps:`, a future version may accept `https://github.com/owner/repo#app-slug` keys; unknown `#…` suffixes must fall back to the bare repo key.
- Values are YAML lists of **task ids** from `manifest.yml` (e.g. `build-planned-features`, not `task 1`). Task ids are the contract end-to-end — never numbers.
- An empty list `[]` means "no tasks for this repo in this bundle"; the wrapper records `not-selected` in the summary and dispatches nothing for that repo.
- A repo absent from `repos:` defaults to **all tasks allowed** (same as no config block at all). This keeps single-repo ad-hoc invocations working.

**Parsing rules** — the wrapper is itself an LLM subagent, so robustness matters:

1. Scan your own invocation prompt for the literal strings `<night-shift-config>` and `</night-shift-config>`. Extract everything between.
2. Parse as YAML. If parsing fails, the delimiter is missing, or the block is empty → treat as "no allowlist supplied". Log **one line** in the final summary: `allowlist: none (running all tasks)`.
3. If a listed task id doesn't appear in `manifest.yml`, warn (one line in the summary: `allowlist warning: unknown task id <id> for <repo>`) and ignore that id. Never crash the run.
4. If a repo URL in `repos:` isn't among the cloned sources, warn (`allowlist warning: repo <url> in config but not cloned`) and ignore.

**How the wrapper applies the allowlist** — in the work-item loop, for each repo:

- Look up the repo's allowlist. Absent → all tasks allowed (this bundle's full task set from `manifest.yml`).
- Intersect the allowlist against the set of this bundle's tasks. If the intersection is empty, record `not-selected` for that repo and do not dispatch any subagents for it.
- Pass `allowed_tasks: [<intersection as YAML list>]` to every subagent dispatched for this repo. Subagents forward it to the inner bundle and each task, which self-check their own id against the list and exit silently if not present.

**When the user hand-edits the prompt.** The skill's add/remove/update-repo flows must **read the current routine prompt, parse the YAML, merge the change, and rewrite** — never regenerate from scratch. This preserves any hand-edits the user made in the routines dashboard.

## How the routine lays out repos

When a routine declares multiple `sources[]` entries with `git_repository`, the remote environment clones each one as a sibling directory at the top of the working tree:

```
<working dir>/
├── repo-a/        ← .git inside
├── repo-b/
└── repo-c/
```

Discover dynamically — do not hardcode paths:

```bash
ls -1 -d */ 2>/dev/null
( cd "$dir" && git rev-parse --show-toplevel 2>/dev/null )
```

A directory is a repo if `git rev-parse --show-toplevel` succeeds.

## The loop — one isolated subagent per work-item

**Critical:** each work-item must be processed in its own subagent (via the `Task` tool) so the main wrapper's context window does not accumulate state across repos. The main wrapper only stores a single one-line result per work-item.

A **work-item** is either `{repo, app_path: null, scoped_config}` (single-app repo) or `{repo, app_path: "apps/<slug>", scoped_config}` (one per app in a monorepo). See **Discovery** below for how work-items are derived.

For each work-item, in deterministic order (repo directory name, then app path):

1. From the main wrapper, briefly `cd` into the repo to:
   - Run `git status --porcelain` — if dirty, record `dirty-skip` and continue (whole repo, not per-app).
   - Check opt-out signals. Record `opted-out` and continue if **any** of these are true:
     - A file `.nightshift-skip` exists at the repo root.
     - `CLAUDE.md`, `AGENTS.md`, or `README.md` contains a line `Night Shift: skip`.
   - Parse the **Night Shift Config** section in `CLAUDE.md` (optional). Build the list of work-items as described under **Discovery**.
   - Capture the absolute repo path. `cd` back to the parent directory.
2. For each work-item derived from this repo, dispatch a `Task` subagent with a self-contained prompt that:
   - Tells the subagent its working directory (the absolute repo path).
   - Tells it which app it is scoped to (`app_path`, or `—` for repo-wide).
   - Passes the **scoped config** (test command, build command, key pages, plans dir) resolved for this app.
   - Gives it the URL of the inner bundle to fetch and execute.
   - Instructs it to perform all of the inner bundle's work **inside `app_path`** for tasks marked `scope: app` in `manifest.yml`, and **repo-wide** for tasks marked `scope: repo`.
   - Asks it to return **one single line** to the wrapper, format: `<status> | PR: <url or —> | <terse note>` where status ∈ {`ok`, `silent`, `failed`}.
3. Capture only that one-line result. Do **not** read or echo the subagent's intermediate work.
4. Move on to the next work-item.

After all work-items for a given repo have been dispatched, run the **per-repo PR body sweep** before moving to the next repo. See "PR body sweep" below.

If a subagent dispatch itself throws an unrecoverable error, record `failed | dispatch error: <reason>` and continue. Never abort the multi-repo run.

## Label sweep (wrapper-level safety net) — run BEFORE the body sweep

After all work-items for a repo have been dispatched and their one-line results captured, the wrapper first runs a **label sweep** so the body sweep below (which finds PRs by label) sees every Night Shift PR. Subagents sometimes drop `--label night-shift` on `gh pr create` or skip the post-create `--add-label` step; this sweep adds the missing label by matching on the Night Shift PR title prefix instead. Idempotent — only edits PRs that don't already carry the label.

```bash
( cd "$REPO_PATH" && \
  gh pr list --state open --json number,title,labels --jq '
    .[] | select(.title | startswith("night-shift/"))
        | select((.labels | map(.name)) | index("night-shift") | not)
        | .number' \
    | xargs -I{} -r gh pr edit {} --add-label night-shift )
```

Why title-prefix, not label: by definition the only way a PR can be missing the label is if the subagent failed to apply it — so a label-based filter would miss exactly the cases this sweep exists to repair. The `night-shift/` title prefix is the contract every task already enforces (`night-shift/plan:`, `night-shift/bug:`, `night-shift/issue:`, etc.), so it's a reliable secondary key.

Each `multi-*.md` wrapper inlines this exact block in its per-repo loop, **immediately before** the body sweep below.

## PR body sweep (wrapper-level safety net)

After the label sweep above, the wrapper runs a **PR body sweep** in that repo to repair any subagent that skipped its per-task post-create ritual. The sweep is idempotent — it only modifies bodies that contain literal `\n` sequences.

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

Why this exists: the per-task post-create ritual already includes the same fix, but a subagent reading a dense task file sometimes runs `gh pr create` and then returns without continuing through the ritual. The wrapper-level sweep catches that case before the run ends, so a flattened body never survives the night.

Why label-based, not URL-extraction: result line formats vary by wrapper (`PR:` vs `PRs:` vs combined-status). Sweeping every open `night-shift`-labelled PR in the repo is robust to result-line drift and also opportunistically repairs older PRs that may still be open from earlier runs.

Each `multi-*.md` wrapper inlines this exact block in its per-repo loop. Do **not** delete it from a wrapper without also deleting it from the others — the consistency is the whole point.

## Scout open sibling PRs before editing

Before a task makes its first edit, run this once to see what sibling Night Shift PRs are already open:

```
gh pr list --state open --label night-shift \
  --json number,title,files \
  --jq '[.[] | {n:.number, t:.title, f:[.files[].path]}]'
```

Treat the result as advisory, not a gate:

- If the list is empty or the command errors, proceed as normal.
- If any returned PR's `f` (files) overlaps with files this task will edit, read that PR's diff with `gh pr diff <n>` and write your changes so they remain compatible with the pending PR. Do not wait for the sibling PR to merge — `--auto` will handle ordering later.
- If there is no overlap, proceed as normal.

This is a hint, not a gate. Never abort a task because scouting failed or produced unexpected output. The merge queue / `--auto` still serves as the backstop for conflicts that slip through.

## PR body formatting

**Critical:** Always pass PR bodies via `--body-file`, never `--body "..."`. Inline `--body` strings are repeatedly serialized as one-liners with literal `\n` instead of newlines (observed in practice — even when the task template uses a quoted HEREDOC, the agent sometimes flattens the body to a single-line string). GitHub then renders the `\n` as visible text and the entire PR shows as one unbroken paragraph.

The required pattern is **always**:

```
cat > /tmp/night-shift-pr-body.md <<'EOF'
## Summary
- first change
- second change

---
_Run by Night Shift • <bundle>/<task>_
EOF

gh pr create --title "..." \
  --label night-shift \
  --body-file /tmp/night-shift-pr-body.md
```

The HEREDOC writes to a file; `--body-file` reads the file. There is no shell-string flattening step in between, so newlines survive. The single quotes around `'EOF'` also prevent shell variable expansion / backslash interpretation inside the body — what you write is exactly what lands in the PR.

**Forbidden patterns** (any of these will silently produce a `\n`-broken PR body):
- `--body "..."` — even with `$(cat <<EOF...)`. Don't do this.
- `--body "Summary\n- first\n- second"` — literal `\n` characters.
- `--body "$(printf ...)"` — printf interprets escapes inconsistently.
- Any body construction that goes through a shell variable with embedded newlines.

Use `/tmp/night-shift-pr-body.md` as the conventional filename — short, predictable, easy to inspect post-mortem if a PR body looks wrong. The file can be overwritten on each PR creation; cleanup is not required.

Each task file contains the body template inside the HEREDOC block. Follow the template structure exactly.

## Standardized PR title, labels, and footer (every task)

Every PR opened by Night Shift must follow these conventions so reviewers can filter, attribute, and audit the work consistently across all tasks and bundles.

### PR title format
Always `night-shift/<area>: <description>`. Slash + colon. The `<area>` is the task's short slug (`bug`, `a11y`, `tests`, `plan`, `docs`, `changelog`, `suggestions`, `adr`, `seo`, `perf`, `security`, `i18n`, `issue`). Never use the parens form `night-shift(<area>):` for PR titles — the parens form is reserved for `git commit -m` messages on direct-to-main work, not for PR titles. When the task is scoped to an app, the title includes `<app_path> — ` after the colon.

### Labels (created at wrapper level, applied at task level)
Every `gh pr create` call must add the single `night-shift` label. The bundle is already obvious from the PR title (`night-shift/plan:`, `night-shift/bug:`, etc.), so per-bundle sub-labels (`night-shift:plans` etc.) are intentionally **not** used — one label is enough to filter every Night Shift PR.

**Label creation is a wrapper precondition, not a per-task step.** Each multi-runner wrapper, before dispatching any subagents for a given repo, runs the following block once per repo (after `cd`-ing in for the dirty / opt-out checks):

```
gh label create night-shift --color "0e8a16" --description "Automated by Night Shift" 2>/dev/null || true
```

The create is cheap and idempotent. **Do this once per repo per wrapper run.** Subagents inherit the label and only need to apply it.

Tasks **only** pass the flag, never call `gh label create` themselves:
```
gh pr create --title "night-shift/<area>: ..." \
  --label night-shift \
  --body "..."
```

### PR creation throttle (every task, no exceptions)

Every `gh pr create` call must be **preceded** by a gap check and **followed** by a timestamp write. This staggers PRs across all Night Shift subagents in the same routine run so downstream CI concurrency groups don't prune queued runs faster than they can dispatch.

Why this exists: target repos with `concurrency: { cancel-in-progress: false }` on a shared group (one per repo, not per PR) prune older queued runs whenever a third PR queues against the group. Night Shift fan-out used to open 6–10 PRs in ~10 minutes (work-on-issues × 3, work-on-jira × 3, plus plan subagents finishing back-to-back), and most of the queued workflow runs got pruned before they could start. A 90-second floor between PR creations gives GitHub time to dispatch the previous workflow out of the queue before the next PR arrives.

Why the lock is `/tmp/night-shift-pr-last-created`: every Task subagent in a routine shares the same filesystem, so the timestamp coordinates across both within-subagent loops (work-on-issues opening 3 PRs in series) and across-subagent fan-out (multi-plans dispatching 10+ subagents whose final action is `gh pr create`). One throttle, both layers.

The block is small enough to inline. Tasks paste it verbatim around their existing `gh pr create`:

```
# Stagger PR creation. Spec: bundles/_multi-runner.md → "PR creation throttle".
LAST=/tmp/night-shift-pr-last-created
if [ -f "$LAST" ]; then
  ELAPSED=$(( $(date +%s) - $(cat "$LAST") ))
  [ "$ELAPSED" -lt 90 ] && sleep "$((90 - ELAPSED))"
fi
# … gh pr create … (existing block)
date +%s > /tmp/night-shift-pr-last-created
```

This is **not** a substitute for fixing pathological CI configs (e.g. a shared concurrency group that takes 10+ minutes to drain). It is polite pacing — it eliminates the "burst of 7 PRs in 10 minutes" failure mode and reduces cancellations to whatever the steady-state queue depth allows. Repos whose CI suites still cancel under 90s pacing need their workflow concurrency redesigned (per-PR groups, or `cancel-in-progress: true`); Night Shift can't fix that from the outside.

### Post-create ritual (every task, no exceptions)

Every `gh pr create` call must capture the URL and immediately run this block:

```
# Stagger PR creation. Spec: bundles/_multi-runner.md → "PR creation throttle".
LAST=/tmp/night-shift-pr-last-created
if [ -f "$LAST" ]; then
  ELAPSED=$(( $(date +%s) - $(cat "$LAST") ))
  [ "$ELAPSED" -lt 90 ] && sleep "$((90 - ELAPSED))"
fi

PR_URL=$(gh pr create --title "night-shift/<area>: ..." \
  --label night-shift \
  --body-file /tmp/night-shift-pr-body.md)
date +%s > /tmp/night-shift-pr-last-created

# (1) Re-assert the label idempotently. `gh pr create --label X` silently drops X
# if the label does not exist on the target repo, which is how PRs historically
# landed label-less. `gh pr edit --add-label` is idempotent and surfaces errors.
gh pr edit "$PR_URL" --add-label night-shift

# (2) Verify title format. The PR title MUST match 'night-shift/<area>: '. The
# parens form `nightshift(<area>):` is reserved for direct-to-main commit
# messages and must not appear on PR titles.
TITLE=$(gh pr view "$PR_URL" --json title -q .title)
if ! echo "$TITLE" | grep -qE '^night-shift/[a-z]+(:| —)'; then
  echo "ERROR: PR title does not match 'night-shift/<area>: …' convention: $TITLE" >&2
  echo "Rename the PR via 'gh pr edit \"$PR_URL\" --title ...' before continuing." >&2
fi

# (3) PR body sanity-fix. Even with `--body-file`, subagents sometimes pass a
# body string that contained literal `\n` sequences (backslash + n) instead of
# real newlines — rendering the whole PR as one unbroken paragraph on GitHub.
# Detect that case and rewrite the body with real newlines.
BODY=$(gh pr view "$PR_URL" --json body -q .body)
case "$BODY" in *'\n'*) printf '%s' "$BODY" | python3 -c "import sys;sys.stdout.write(sys.stdin.read().replace(chr(92)+chr(110),chr(10)))" > /tmp/night-shift-body-fix.md && gh pr edit "$PR_URL" --body-file /tmp/night-shift-body-fix.md ;; esac

# (4) Arm auto-merge. The fallback handles repos with a merge queue, where
# GitHub sets the merge method itself and rejects the explicit --squash.
gh pr merge "$PR_URL" --auto --squash 2>/dev/null || gh pr merge "$PR_URL" --auto || true
```

Why each step matters:

- **Label re-assertion** fixed the recurring "PR landed with no night-shift label" class of failures. When the `night-shift` label doesn't exist yet on the target repo, `gh pr create --label` silently drops the flag — and the review-gate workflow then auto-passes the PR because the label-match fails, meaning it can merge with zero human approval. Re-asserting via `gh pr edit` is idempotent and produces a visible error if the label truly can't be applied.
- **Title check** catches subagents that improvise (`nightshift(docs):`, `nightshift/plan:`, etc.) and warn-logs them without failing the task — a reviewer can fix the title manually before merging.
- **PR body sanity-fix** defends against the `\n`-flattening failure mode. Wrapper-level checks exist too (see step 4 of the work-item loop above), but running the fix at task level — right after `gh pr create` — catches it before auto-merge ever sees the body and before the PR is visible for more than a few seconds. Keeps both layers; each catches what the other misses.
- **Arm auto-merge** without this, Night Shift PRs sit on their original tree all day. When sibling PRs merge first, each remaining PR goes stale against `main` (missing modules added by siblings, stale CI aggregators, merge conflicts with fresh code). `--auto` does **not** bypass human review or required checks — the PR enters the merge queue only once a reviewer approves in the morning and every required check is green.

If any step fails, log the error but do not fail the task — the PR is already created and a human can remediate. Never abort after a successful `gh pr create`.

### Self-review + one revision (code-touching bundles only)

**Applies to:** every task in the `plans`, `code-fixes`, and `audits` bundles. Docs bundle tasks **skip this step entirely** — their output is already user-readable prose, and a self-review pass mostly produces rewording churn without improving correctness.

**Goal:** catch correctness bugs, dead code, and scope drift in the task's own output before a human reviewer sees the PR in the morning. Same-model self-review isn't a substitute for human review — it's a cheap polish pass that raises the floor on each PR.

**Shape:** exactly **one** review and **at most one** revision commit, on the same branch. No loop, no recursion, no second review of the revision. If the revision breaks tests, revert it and keep the original PR.

This step runs **immediately after the post-create ritual above** (labels applied, title verified, body sanity-fixed, auto-merge armed). Auto-merge is already armed; that's fine — a fresh push to the branch just resets GitHub's check status, and auto-merge won't fire until checks re-pass and a human approves in the morning. Order is: create PR → post-create ritual → self-review → (optional) revision commit → PR body audit note. Do **not** reorder or interleave.

#### Review step

Read the PR's own diff:

```
gh pr diff "$PR_URL"
```

Critique the diff as if a colleague had opened it. **Only act on** concrete items from this list:

- **Correctness** — off-by-ones, missing `await`s, inverted conditionals, missing null checks on values that can actually be null, silent swallowing of errors that must bubble up, obviously-wrong comparisons.
- **Dead code / scope drift** — files touched that are unrelated to the task's stated goal, helpers introduced but not used, leftover `console.log` / `print` / `dbg!` / commented-out blocks, TODOs added as part of this change.
- **Missing error handling at system boundaries** — external IO, user input, external API calls where the rest of the code assumes success.
- **Missing test that the task template explicitly required** — e.g. `find-bugs` requires a failing test that demonstrates the bug. If the diff adds a fix with no test, that qualifies.

**Do not act on** (these produce churn without value — leave them for the human reviewer):

- Naming / style nits ("could be named better", "prefer early return")
- Speculative edge cases that can't be reached from reading the code
- "Nice to have" refactors or abstractions
- Documentation prose improvements
- Anything that would *expand* the PR's scope rather than tighten it

If the review surfaces **zero** actionable items from the "act on" list, the task is done. Do **not** create an empty revision commit. Jump straight to the audit-trail note below ("no actionable issues").

#### Revision step (at most once)

If the review surfaced at least one actionable item:

1. Make the fixes directly on the same branch — **no new branch, no new PR**. Keep the revision minimal; address only what the review flagged. Expanding scope defeats the purpose.
2. Re-run the scoped **test suite** and the scoped **build command**. Both must pass.
3. **If both pass:** commit with message `night-shift: self-review revision` and `git push origin <branch>`. Auto-merge re-evaluates automatically once checks re-run.
4. **If tests or build fail:** revert the revision and keep the original PR:
   ```
   git reset --hard HEAD~1
   git push --force-with-lease origin <branch>
   ```
   Use `--force-with-lease` (not `--force`) so the push aborts if anything else has landed on the branch since the revision commit. If the lease check fails, log it and stop — do not retry with plain `--force`.

**Never** attempt a second revision. If the first revision breaks tests, the original PR stands and humans handle it in the morning.

#### Audit-trail note on the PR body

After the review (and optional revision), append a `## Self-review` section to the PR body so human reviewers can see what the pass did. Read the current body, insert the new section **before** the `---` footer, and rewrite via `--body-file`:

```
gh pr view "$PR_URL" --json body -q .body > /tmp/night-shift-body-current.md
python3 - <<'PY' > /tmp/night-shift-body-next.md
import sys, pathlib
body = pathlib.Path('/tmp/night-shift-body-current.md').read_text()
note = """## Self-review
<one of the three notes below>

"""
# Insert before the first '---' horizontal rule (the footer separator).
# If no '---' is present (shouldn't happen — the footer is mandatory), append at the end.
marker = '\n---\n'
if marker in body:
    head, sep, tail = body.partition(marker)
    sys.stdout.write(head.rstrip() + '\n\n' + note + sep.lstrip('\n') + tail)
else:
    sys.stdout.write(body.rstrip() + '\n\n' + note)
PY
gh pr edit "$PR_URL" --body-file /tmp/night-shift-body-next.md
```

Pick exactly one note:

- `Self-review found no actionable issues.` — when the review surfaced nothing worth acting on.
- `Self-review revision applied: <one-line summary of the fixes>.` — when a revision commit landed cleanly.
- `Self-review surfaced <N> issues but the revision broke tests — reverted. Issues: <terse list>.` — when the revision was reverted.

Keep the note to one short paragraph. The human reviewer reads the diff itself for details.

#### Never (self-review rules)

- **Never loop.** One review, at most one revision. No re-reviewing the revision.
- **Never create a second PR or branch.** The revision amends the same branch; the same PR is the only PR.
- **Never fail the task because self-review flagged issues.** The original PR is already created and armed; self-review can only improve it or leave it untouched.
- **Never use plain `git push --force`.** The revert path uses `--force-with-lease` exclusively.
- **Never run self-review in the `docs` bundle.** Prose churn is not the goal.

### Body footer (last lines of every PR body)
Every PR body must end with this footer block, separated from the body by a horizontal rule:

```
---
_Run by Night Shift • <bundle>/<task-id>_
```

The footer is the only place the bundle + task id appears in the PR — keep it minimal. Tasks that have a Claude Code session URL available (passed by the dispatching wrapper) may add it as a second italic line:

```
---
_Run by Night Shift • <bundle>/<task-id>_  
_[Session log](<session-url>)_
```

The footer is required; the session line is optional. Together they make every PR self-describing for reviewers and auditable from `gh pr list --label night-shift`.

### Body header — `## Plain summary` (first section of every code PR body)

Every PR that touches code (audits, code-fixes, plans, work-on-issues) must open with a `## Plain summary` section before any technical content. This is the section a non-technical stakeholder (PM, designer, customer success) reads to decide if they care about the change. Conventions:

- **1–2 sentences max.** Anything longer is no longer a summary.
- **No internal symbols.** Don't write function names (`createIndividualSurvey`), error classes (`TypeError`), file paths (`apps/intranett/src/lib/actions.ts:2058`), mock fixtures, or stack-trace excerpts. Save those for the technical sections below.
- **Frame the user/stakeholder impact.** "Who was affected, what did they experience, what changes after this fix." If you can't articulate user impact, the change probably belongs in `docs/SUGGESTIONS.md` instead of a PR.
- **Always write the Plain summary in English**, regardless of the project's user language. PR review happens in English across every repo — reviewers, PMs, and external collaborators all read the same GitHub list. User-facing artifacts (CHANGELOG, ADRs, doc refreshes) follow the project's configured doc language; the PR Plain summary does not.
- **No "this PR …" framing.** Just describe the change in plain terms: "Survey creation no longer crashes when …", not "This PR fixes a crash in survey creation when …".

Example for a bug PR like #125:

```
## Plain summary
Staff who created an individual follow-up survey could occasionally hit a generic error with no explanation. They now see a clear error message and can safely retry.
```

Doc-only tasks (changelog, ADR, suggestions, user-guide) skip this section — their entire body is already user-readable. Test-only PRs (`add-tests`) also skip — they have no user impact to describe.

## Run history is the PR list

Night Shift used to write a per-repo `docs/NIGHTSHIFT-HISTORY.md` log file. That file has been removed: every task now opens a PR with the `night-shift` label, and `gh pr list --label night-shift --state all` reproduces the same audit trail without committing housekeeping rows. The bundle is recoverable from the PR title (`night-shift/<area>:`). Subagents return `<status> | PR: <url or —> | <terse note>`; the wrapper uses that only to build the in-memory summary table, not to append to any file.

## Discovery — expanding repos to work-items

After cloning a repo and passing the dirty / opt-out checks, build its work-item list:

1. Parse the **Night Shift Config** section in `CLAUDE.md` (if present).
2. If the config has no `apps:` block, or the config is absent entirely, emit **one work-item** with `app_path: null` and `scoped_config = top-level config` (or defaults — see below).
3. If the config has an `apps:` block:
   - For **each task in the bundle**, look up the task's `scope` in `manifest.yml`.
   - For tasks with `scope: app` (the default), emit **one work-item per `apps[]` entry**. Each work-item has `app_path = apps[i].path` and a `scoped_config` that merges the app entry over the top-level config (app entry wins on any overlap).
   - For tasks with `scope: repo`, emit **one work-item** for the whole repo with `app_path: null` and `scoped_config = top-level config` (ignoring `apps:`).
   - De-duplicate so the same (repo, app_path) work-item isn't dispatched twice within one bundle run.

**Config resolution rule (for `scope: app` tasks):**

```
resolved.test       = app.test       ?? top.test       ?? default
resolved.build      = app.build      ?? top.build      ?? default
resolved.key_pages  = app.key pages  ?? top.key pages  ?? heuristic(app_path)
resolved.plans_dir  = app.plans dir  ?? top.plans dir  ?? "<app_path>/docs"
```

For `scope: repo` tasks, always use the top-level config (never an `apps[i]` block), even in a monorepo.

## Summary table rows — per (repo, app)

When a repo declares `apps:`, the summary table prints **one row per (repo, app_path) work-item** for `scope: app` tasks, plus one row per repo for `scope: repo` tasks. Single-app repos (no `apps:` block) print exactly one row per repo, same as before.

## Defaults when no config exists

If a target repo has no `CLAUDE.md` (or one without a `## Night Shift Config` section), fall back to:

| Setting | Default |
|---|---|
| Test command | First of: `npm test`, `pnpm test`, `yarn test`, `bun test`, `cargo test`, `pytest`, `go test ./...`. If none, test-needing tasks self-skip. |
| Build command | First of: `npm run build`, `pnpm build`, `yarn build`, `bun run build`, `cargo build`, `go build ./...`. If none, build-needing tasks self-skip. |
| Push protocol | `git push origin <branch>` |
| Default branch | Read from `git symbolic-ref refs/remotes/origin/HEAD` |
| Doc language | Match existing docs in `docs/` or `README.md`; fall back to English |
| Key pages | Heuristic: top-level routes in the framework's pages/app directory |
| Task subset | All tasks; each one self-skips when not applicable |

A project with explicit Night Shift Config in `CLAUDE.md` always overrides these defaults.

## Final report

After all repos are processed, print one table and stop. The summary table is the primary run artifact — it appears in the routines dashboard output and is how the user reviews the run the next morning, alongside the PRs themselves (`gh pr list --label night-shift`).

```
Night Shift <bundle-name> — multi-repo summary

| Repo         | App        | Status    | Notes                              |
|--------------|------------|-----------|------------------------------------|
| frisk-survey | —          | ok        | 2 commits pushed                   |
| turbo-site   | apps/web   | ok        | perf sweep PR opened               |
| turbo-site   | apps/admin | silent    | nothing to do                      |
| snippy       | —          | opted-out | .nightshift-skip present           |
| phone-home   | —          | failed    | test command exited 1 in add-tests |
```

The `App` column shows `—` for single-app repos and for `scope: repo` tasks. For monorepos with `apps:` configured, each `scope: app` task gets one row per app.

Status values: `ok`, `silent`, `opted-out`, `dirty-skip`, `failed`. Keep notes terse. No further prose after the table. Do not attempt to write the summary to any external location.
