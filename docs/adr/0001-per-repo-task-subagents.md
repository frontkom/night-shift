# ADR 0001 — Per-repo work runs in isolated Task subagents

## Context

Multi-repo Night Shift wrappers loop over several cloned repositories in a single scheduled session. The first version of the multi-* wrappers ran each repo's bundle inline in the main wrapper agent's context. This had two problems:

1. **Context bloat.** By the time the wrapper reached repo 3, its context was full of repo 1's exploration. Quality dropped on later repos.
2. **No failure isolation.** A failure mid-repo could derail the wrapper's overall summary or affect handling of subsequent repos.

## Decision

Each target repository is processed in its own `Task` subagent dispatch. The main wrapper:

- Briefly `cd`s into the repo to check `git status` and opt-out signals.
- Captures the absolute path.
- Dispatches a subagent with a self-contained prompt that includes the repo path and the bundle URL.
- Captures **only** a one-line result string from the subagent.
- Never reads or echoes the subagent's intermediate output.

This means each repo gets a fresh context window for its work, and the main wrapper's context stays tiny regardless of how many repos are processed.

## Consequences

- **Pro:** Linear scaling — adding more repos to a trigger doesn't degrade quality of later repos.
- **Pro:** Failure of one repo's subagent does not affect the others.
- **Pro:** The remote environment supports parallel async dispatch, so the wrapper actually finishes faster than serial would.
- **Con:** The main wrapper has less visibility into per-repo details. Mitigated by the labelled PR each task opens (`gh pr list --label night-shift`) plus the one-line subagent result the wrapper aggregates into its summary table.
- **Con:** Requires the `Task` tool to be in `allowed_tools` for the trigger. If unavailable, the wrapper falls back to inline execution and loses context isolation.
