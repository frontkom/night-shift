# Triage CI Failures on Open Night Shift PRs

For each open `night-shift`-labelled PR in this repo, examine failed and cancelled check runs, classify each one as caused by the PR's own changes or not, post a triage comment, and re-run the cancelled / clearly-unrelated checks. **No new PRs are opened by this task.** All output is comments on existing PRs.

The goal is to take the morning cleanup pain off the human reviewer's plate: by the time they sit down at the keyboard, every red check on a Night Shift PR already has a comment explaining whether it's the PR's fault or noise.

## Read project config first
Read `CLAUDE.md` → `## Night Shift Config` for default branch and any project-specific notes. The task itself does not need test/build commands — it only reads CI history.

If the dispatcher passed `allowed_tasks` and `triage-ci-failures` is not in it, exit silently.

## Steps

1. **Discover PRs to triage.** List every open `night-shift`-labelled PR:
   ```
   gh pr list --label night-shift --state open --json number,title,headRefOid,headRefName,files
   ```
   Print a discovery summary line before any per-PR work — this is the single best signal that discovery is working:
   ```
   Discovered open Night Shift PRs: #<n>, #<n>, ... (N total).
   ```
   If `N == 0`, print `Discovered open Night Shift PRs: none.` and exit silently with `silent | no open PRs to triage`.

2. **For each PR, fetch its check runs.** Use the GraphQL flavor — REST `/check-runs` paginates awkwardly and misses workflow-level conclusions:
   ```bash
   gh pr checks "$PR_NUM" --json name,state,conclusion,link \
     | jq '[.[] | select(.state == "completed") | select(.conclusion == "failure" or .conclusion == "cancelled" or .conclusion == "timed_out")]'
   ```
   The interesting set is `conclusion ∈ {failure, cancelled, timed_out}`. Skip checks with `conclusion = success`, `skipped`, or `neutral`. Skip checks still `state ∈ {pending, queued, in_progress}` — they haven't reached a verdict yet, so triage them next run.

3. **For each interesting check, classify and act.** The `link` field points to the workflow run page; extract the run ID from the URL (it's the trailing `/runs/<id>` segment). Then:

   ### Idempotency check (skip work that's already been done)
   Before posting any comment, scan the PR's existing comments for a triage marker matching this exact (PR, run-id, check-name) tuple:
   ```bash
   MARKER="<!-- night-shift-triage: pr=$PR_NUM run=$RUN_ID check=$CHECK_NAME -->"
   if gh pr view "$PR_NUM" --json comments --jq '.comments[].body' | grep -qF "$MARKER"; then
     # Already triaged this exact run — skip silently.
     continue
   fi
   ```
   This is the only thing standing between Night Shift and posting the same comment 5 nights in a row on a PR that nobody has touched.

   ### Classify the failure
   For `conclusion = cancelled`:
   - **Bucket: cancelled-by-concurrency.** GitHub cancellations on Night Shift PRs are almost always shared-concurrency-group prunes (see `bundles/_multi-runner.md` → "PR creation throttle" for the long version). No need to fetch logs.
   - **Action:** post a comment explaining the cancellation, then re-run the workflow. By the time triage fires (early morning), the upstream CI queue is usually drained, so the re-run completes cleanly.

   For `conclusion = failure` or `timed_out`:
   - Fetch the failed-job log tail (last ~60 lines) so the comment shows the human exactly what broke without making them click through:
     ```bash
     LOG_TAIL=$(gh run view "$RUN_ID" --log-failed 2>/dev/null | tail -n 60)
     ```
   - Fetch the PR's changed file list:
     ```bash
     PR_FILES=$(gh pr view "$PR_NUM" --json files --jq '.files[].path')
     ```
   - **Decide: related vs unrelated.** Read the log tail and ask: which file or test does the failure point at? Compare that path/area against `PR_FILES`.
     - **Bucket: failure-related** — the failing test/file is one the PR touches, or imports from a file the PR touches, or is in the same module as the PR's diff. The PR's changes are the most likely cause.
     - **Bucket: failure-unrelated** — the failing test/file is in an entirely different area than what the PR touched (different app, different package, different feature). The PR can't plausibly be the cause; treat as flake or pre-existing red.
   - When in doubt, prefer **related** — false-positive "unrelated" comments are worse than false-positive "related" comments. A reviewer can ignore a wrong "related" diagnosis; a wrong "unrelated" diagnosis tells them the bot can't be trusted.

   ### Post the comment + take action
   Always include the marker as the first line of the body so the idempotency check above works on the next run.

   **Cancelled by concurrency** — comment + re-run:
   ```
   $MARKER

   ## CI triage: `$CHECK_NAME` cancelled

   This run was **cancelled**, almost certainly by a shared concurrency group on the workflow (the queue gets pruned when 3+ runs are pending). The PR's own code is not involved.

   Re-running now — by morning the upstream queue has usually drained.

   ---
   _Run by Night Shift • triage-ci/triage-ci-failures_
   ```
   Then re-run:
   ```bash
   gh run rerun "$RUN_ID" 2>/dev/null || gh run rerun "$RUN_ID" --failed 2>/dev/null || true
   ```

   **Failure unrelated** — comment + re-run once:
   ```
   $MARKER

   ## CI triage: `$CHECK_NAME` failed (likely flake / unrelated)

   The failing test or job is in an area this PR doesn't touch:
   - **PR diff (top-level):** <comma-separated list of top-level dirs touched, e.g. `apps/intranett/`, `packages/ui/`>
   - **Failure location:** <file or test name extracted from the log>

   The diff and the failure don't intersect, so this is most likely a pre-existing red baseline or a flake. Re-running once to confirm.

   <details><summary>Failed-job log tail</summary>

   ```
   <last ~30 lines of LOG_TAIL — trim to the most relevant chunk>
   ```

   </details>

   ---
   _Run by Night Shift • triage-ci/triage-ci-failures_
   ```
   Then re-run:
   ```bash
   gh run rerun "$RUN_ID" 2>/dev/null || gh run rerun "$RUN_ID" --failed 2>/dev/null || true
   ```

   **Failure related** — comment only, no re-run:
   ```
   $MARKER

   ## CI triage: `$CHECK_NAME` failed (likely caused by this PR)

   The failing test/job is in code this PR touches:
   - **PR diff (top-level):** <list>
   - **Failure location:** <file or test>

   <details><summary>Failed-job log tail</summary>

   ```
   <last ~30 lines of LOG_TAIL>
   ```

   </details>

   Suggested next step: <one-line hint, e.g. "the test asserts X but the change in <file> appears to make it Y" — keep this terse and only include if you're confident; otherwise skip it>.

   No re-run — failures that look caused by the PR's diff need a human read.

   ---
   _Run by Night Shift • triage-ci/triage-ci-failures_
   ```
   Do **not** re-run. Re-running a real failure burns CI minutes for no value and obscures the original red signal.

   ### Post via `--body-file`, never inline
   Same rule as `bundles/_multi-runner.md` → "PR body formatting": shell-string flattening turns embedded newlines into literal `\n`. Always:
   ```bash
   cat > /tmp/night-shift-triage-comment.md <<EOF
   $MARKER

   ## CI triage: ...
   ...
   EOF
   gh pr comment "$PR_NUM" --body-file /tmp/night-shift-triage-comment.md
   ```
   The HEREDOC must use unquoted `EOF` here so `$MARKER` and `$LOG_TAIL` interpolate.

4. **Per-PR cleanup.** After processing all interesting checks for a PR, move on. Do not modify the PR's body, do not close the PR, do not change labels.

5. **Limits.** Cap at **20 PRs per run** to keep the routine bounded. If discovery returns more, process the 20 oldest-by-PR-number and report the remainder as deferred in the summary line.

## Final return value

Return EXACTLY ONE LINE to the wrapper in this format:
```
<ok|silent|failed> | triaged: <N> PRs, <C> comments posted, <R> reruns triggered | <terse note, max 60 chars>
```
- `ok` if at least one comment was posted or one re-run triggered.
- `silent` if no open Night Shift PRs were found, or all of them were already triaged (idempotency skips). Treat this as success — there is nothing to do.
- `failed` only if the discovery query itself errored.

## Rules
- **Never re-run a "related failure".** Burning CI minutes on a real bug is wasteful and confusing.
- **Never post the same comment twice.** The marker check is non-negotiable; without it the bot becomes a daily noise machine.
- **Never modify the PR diff or merge state.** This task is read-only with respect to PR content; the only writes are PR comments and `gh run rerun`.
- **Skip non-`night-shift` PRs.** This task triages Night Shift's own output, not arbitrary human PRs.
- **English-only comments.** Triage comments are read by reviewers across teams; same convention as PR plain summaries (see `bundles/_multi-runner.md` → "Body header — Plain summary").
