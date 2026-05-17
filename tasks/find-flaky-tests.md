# Find Recurring Flaky Tests

Mine recent CI history on the default branch for tests that fail nondeterministically (sometimes pass, sometimes fail without an intervening code change), pick the **single** worst offender whose nondeterminism is identifiable from the test's source, and open one focused PR that fixes the root cause or — only as a last resort — quarantines the test with a tracking comment. **One PR per night, one test per PR.**

The goal is to keep Night Shift's other PRs trustable. Every Night Shift PR is gated on a green CI baseline; recurring flakes train reviewers to ignore red checks, which is the path to merging a real regression.

## Read project config first
Read `CLAUDE.md` → `## Night Shift Config` for test command, build command, default branch, and push protocol. Note any project-specific test conventions (retry tolerance, quarantine directory, fixed-seed conventions).

If the dispatcher passed `allowed_tasks` and `find-flaky-tests` is not in it, exit silently.

**Audit scope.** Honor `Audit scope`, `Exclude`, and the hardcoded baseline exclude from `bundles/_multi-runner.md` → "Optional config fields". A flake whose source lives outside scope is out of scope for this task — skip it and consider the next candidate.

**Scoping.** This task runs at `scope: repo` because CI history is repo-wide. The chosen fix may live under a single app; that's fine, just keep the branch/PR name unscoped.

## High bar — default is silent
Open a PR only when **all** of these hold:
- The test has failed in **≥ 2 distinct CI runs** on the default branch in the last 14 days, **and** has passed in at least one other run on the same or an adjacent commit (i.e. the failures aren't explained by a real code change introducing a regression).
- Reading the test's source makes the nondeterminism's cause obvious — a missing `await`, an unseeded RNG, `Date.now()` / `new Date()` without freezing, shared module-level state across tests, a race on filesystem or DB cleanup, ordering assumptions on Map/Set iteration, timezone or DST dependency, a `setTimeout` / `sleep` shorter than the work it's waiting on, etc.
- The fix is mechanical and localized to the test file (or one shared helper). If fixing the flake would require a substantive change to product code, exit silent — that's a bug, not a flake.

If no candidate clears that bar, exit silently. **Zero flakes is the correct outcome on most nights** — speculative quarantine PRs erode the same CI trust this task is meant to protect.

## Steps

1. **Discover existing work to avoid duplicates.**
   ```
   gh pr list --search "night-shift/flake in:title" --state open
   ```
   If an open `night-shift/flake` PR already exists, exit silently — finish one before queueing another.

2. **List recent failed CI runs on the default branch.** Cap at the last 50 failed runs or the last 14 days, whichever is smaller:
   ```bash
   DEFAULT_BRANCH=$(gh repo view --json defaultBranchRef --jq .defaultBranchRef.name)
   gh run list \
     --branch "$DEFAULT_BRANCH" \
     --status failure \
     --limit 50 \
     --created ">=$(date -u -v-14d +%Y-%m-%d 2>/dev/null || date -u -d '14 days ago' +%Y-%m-%d)" \
     --json databaseId,headSha,workflowName,createdAt,conclusion
   ```
   If the result is empty, print `Discovered failed runs: none.` and exit silently with `silent | no failed runs in window`.

3. **For each failed run, extract the failing test names.** The format varies by ecosystem; try the cheap path first (log tail, ~200 lines) before deeper artifact parsing:
   ```bash
   gh run view "$RUN_ID" --log-failed 2>/dev/null | tail -n 200
   ```
   Look for the project's test framework markers, e.g.:
   - Vitest / Jest: lines starting with `FAIL ` followed by a file path; `✗`/`×` prefixed lines.
   - PHPUnit: `1) Tests\…::testName` blocks under `There was 1 failure:`.
   - pytest: lines matching `FAILED tests/… - `.
   - Go: `--- FAIL: TestName`.
   - RSpec: `Failures:` block, each numbered failure has `# ./spec/...`.
   If the project uploads JUnit XML artifacts, `gh run download "$RUN_ID" -p '*junit*'` is the more reliable path — use it when log parsing is ambiguous.
   Record `(test_identifier, run_id, head_sha)` for each failure. Keep the test identifier stable (`path::test_name` or framework-equivalent).

4. **Cross-reference with passing runs to detect non-determinism.** For each candidate test identifier, look for a successful run of the same workflow on the same or an adjacent commit:
   ```bash
   gh run list \
     --branch "$DEFAULT_BRANCH" \
     --status success \
     --workflow "$WORKFLOW_NAME" \
     --limit 50 \
     --json databaseId,headSha,createdAt
   ```
   A test is a real flake candidate iff:
   - It failed in ≥ 2 distinct runs (different `run_id`), **and**
   - There exists at least one successful run of the same workflow within 3 commits of one of the failing commits (this rules out "real regression that was later fixed" — those have a clean before-and-after, not interleaving).

   Build a ranked list (most failures first). If the top candidate fails this gate, walk down the list. Stop walking after 5 candidates — beyond that the signal-to-noise is too low.

5. **Pick one test and read it.** Open the test source and the helpers it imports. Identify the nondeterminism. If you can't name the cause in one sentence from the code (not from speculation), drop this candidate and consider the next — or exit silent.

6. **Decide the fix.** In priority order:
   1. **Root-cause fix in the test file.** Add the missing `await`, replace `new Date()` with the project's freeze helper, seed the RNG, isolate shared state, fix the race. This is the default and the only fix that improves CI long-term.
   2. **Tighten the test's setup/teardown helper** when the cause is in shared infra (a fixture, a test-DB reset) and the change is still scoped to test code. Verify no other test relies on the looser behavior.
   3. **Quarantine (last resort).** Only when (1) and (2) are out of reach in a single localized change. Move the test to the project's quarantine directory / `skip` / `xfail` / `t.Skip` per project convention, with a comment `// flaky: see <issue-url>` pointing at a tracking GitHub issue you open in the same PR. Quarantines without a tracking issue are not allowed — they rot.

   **Do not** add blanket retry decorators. Per-test retry hides flakes instead of fixing them and the project may not have an established retry convention.

7. **Branch and verify locally.**
   ```
   git checkout -b night-shift/flake-YYYY-MM-DD-<test-slug>
   ```
   Make the change. Run the **scoped test suite** at least **5 times in a row** locally:
   ```bash
   for i in 1 2 3 4 5; do <project's test command for this file> || exit 1; done
   ```
   Five clean passes is the minimum — a single pass is not evidence of a flake fix. Also run the project's full **build command** once to confirm no collateral damage.

8. **Open the PR.** Always use `--body-file`, never inline `--body`. The PR body must lead with the standard `## Plain summary` section (English, no symbol names — see `bundles/_multi-runner.md` → "Body header — Plain summary"):
   ```bash
   cat > /tmp/night-shift-pr-body.md <<'EOF'
   ## Plain summary
   <1-2 English sentences. Who was affected: typically "the team", since this fixes CI noise. What changes now: the named test (described in plain words, not by identifier) no longer fails at random.>

   ## Flake
   <Test identifier, file:line, and one-sentence statement of the cause: e.g. "asserts on Map iteration order, which is insertion-order in V8 but the test seeds entries from a Set, whose iteration order is unspecified.">

   ## Evidence
   <N failing runs / M passing runs over the 14-day window. List 2-3 run URLs. Note the commit range so the reviewer can confirm there's no real regression in between.>

   ## Fix
   <One paragraph. Root-cause fix, helper change, or quarantine — name which. If quarantine, link the tracking issue created in the same PR.>

   ## Local verification
   <5x consecutive passes of the test command (paste the command). Full build pass.>

   ---
   _Run by Night Shift • audits/find-flaky-tests_
   EOF

   # Stagger PR creation. Spec: bundles/_multi-runner.md → "PR creation throttle".
   LAST=/tmp/night-shift-pr-last-created
   if [ -f "$LAST" ]; then
     ELAPSED=$(( $(date +%s) - $(cat "$LAST") ))
     [ "$ELAPSED" -lt 90 ] && sleep "$((90 - ELAPSED))"
   fi
   PR_URL=$(gh pr create --title "night-shift/flake: <short description of the test>" \
     --label night-shift \
     --body-file /tmp/night-shift-pr-body.md)
   date +%s > /tmp/night-shift-pr-last-created

   # Post-create ritual — REQUIRED after every gh pr create. Spec: bundles/_multi-runner.md.
   gh pr edit "$PR_URL" --add-label night-shift
   BODY=$(gh pr view "$PR_URL" --json body -q .body)
   case "$BODY" in *'\n'*) printf '%s' "$BODY" | python3 -c "import sys;sys.stdout.write(sys.stdin.read().replace(chr(92)+chr(110),chr(10)))" > /tmp/night-shift-body-fix.md && gh pr edit "$PR_URL" --body-file /tmp/night-shift-body-fix.md ;; esac
   gh pr merge "$PR_URL" --auto --squash 2>/dev/null || gh pr merge "$PR_URL" --auto || true
   ```

   **Self-review.** After the post-create ritual, run the **Self-review + one revision** step from `_multi-runner.md` before returning your one-line result. One review, at most one revision commit, same branch; if the revision breaks tests, revert with `git push --force-with-lease` and keep the original PR.

## Final return value

Return EXACTLY ONE LINE to the wrapper in this format:
```
<ok|silent|failed> | flake-fix: <pr-url-or-none> | <terse note, max 60 chars>
```
- `ok` if a PR was opened.
- `silent` if no candidate cleared the high bar, or an open `night-shift/flake` PR already exists.
- `failed` only if the CI history queries themselves errored.

## Rules
- **One PR per night, one test per PR.** No bundling. Fixing two flakes in one PR makes the fix harder to review and harder to revert.
- **Never speculate.** If you can't name the cause from reading the test, exit silent.
- **Never blanket-retry.** Retry decorators hide flakes; this task fixes them.
- **Never quarantine without a tracking issue.** Quarantines must come with a follow-up.
- **Five-pass local verification.** A single pass is not evidence.
- **English PR body.** Same convention as other audit tasks.
