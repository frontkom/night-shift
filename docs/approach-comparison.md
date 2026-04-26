# Night Shift: Approach Comparison

Comparison of different approaches for running nightly maintenance across multiple repositories.

## Approaches Considered

### 1. Remote Triggers (current approach)

Claude Code's scheduled remote triggers fire nightly, each running a multi-repo wrapper prompt that discovers repos, creates work-items, and dispatches isolated subagents per repo.

**Pros:**
- Zero infrastructure — no workflow files or CI config per repo
- Single control plane — one `manifest.yml` + skill manages everything
- Works with any local repo, not just GitHub-hosted ones
- No CI minutes cost
- Runs when laptop is off (API-based)

**Cons:**
- Audit trail is the labelled PR list (`gh pr list --label night-shift`) plus the routines dashboard, not a native CI/CD UI
- Less visibility for team collaboration

### 2. GitHub Actions with claude-code-action

Use `anthropics/claude-code-action@v1` in a scheduled workflow per repo. Each repo gets a `.github/workflows/claude-nightly.yml` with a cron trigger and a tailored prompt.

**Pros:**
- Runs on GitHub's infra (no local dependency)
- Native PR-based review workflow
- Per-repo audit trail in GitHub Actions UI
- Good for team visibility

**Cons:**
- Requires workflow file + secrets setup per repo
- Config scattered across repos
- CI minutes cost on top of API credits
- Only works with GitHub-hosted repos

### 3. Local bash loop / cron

Simple `while true` loop or cron job running `claude -p` for each repo.

**Pros:**
- Dead simple to set up
- Full control over execution

**Cons:**
- Dies if machine sleeps or loses power
- No built-in parallelism or isolation
- Manual log management

### 4. Tmux / screen session

Leave an interactive Claude Code session running in a detached terminal.

**Pros:**
- Interactive session available for debugging
- Simple

**Cons:**
- Requires machine to stay on
- Single session, hard to scale across repos
- No scheduling built in

## Comparison

| | Remote Triggers | GitHub Actions | Local cron | Tmux |
|---|---|---|---|---|
| Runs when laptop is off | Yes | Yes | No | No |
| Setup effort per repo | Select tasks in picker | Workflow file + secrets | Script entry | Manual |
| Central config | Single manifest | Scattered across repos | Single script | None |
| Cost | API credits only | API credits + CI minutes | API credits | API credits |
| Audit trail | Labelled PRs + routines dashboard | GitHub Actions logs + PRs | Log files | None |
| Non-GitHub repos | Yes | No | Yes | Yes |
| Team visibility | Low | High | Low | Low |
| Parallel execution | Yes (subagents) | Yes (matrix/parallel jobs) | Manual | No |

## Recommendation

**Remote Triggers** (current approach) is the best fit for a single developer managing multiple repos:
- Minimal setup overhead
- Centralized configuration
- No infrastructure cost beyond API credits
- Works regardless of where repos are hosted

**GitHub Actions** becomes the better choice when:
- Working with a team that needs visibility into nightly runs
- PR-based review workflows are important
- You want GitHub-native audit trails
- All repos are GitHub-hosted
