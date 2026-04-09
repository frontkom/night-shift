"""Reference implementations of the behaviours that wrappers and the skill
must match. Exists so the LLM prompts can be tested against concrete,
deterministic specs.

Nothing here runs in production — the wrappers and the skill are markdown
prompts executed by an LLM. This module encodes the *intended* semantics of
those prompts so we can lock in the design with tests.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import yaml


# ---------------------------------------------------------------------------
# Allowlist parsing (matches bundles/_multi-runner.md → "Per-repo task allowlist")
# ---------------------------------------------------------------------------

OPEN = "<night-shift-config>"
CLOSE = "</night-shift-config>"


@dataclass
class AllowlistParseResult:
    repos: dict[str, list[str]]  # repo_url -> list of task ids
    warnings: list[str] = field(default_factory=list)
    fell_back: bool = False  # True if absent or malformed; equivalent to all-allowed


def parse_allowlist(prompt: str) -> AllowlistParseResult:
    """Scan a wrapper invocation prompt for the <night-shift-config> block.

    Absent or malformed → fell_back=True, repos={} (all-allowed semantics).
    """
    if OPEN not in prompt or CLOSE not in prompt:
        return AllowlistParseResult(repos={}, fell_back=True)
    try:
        start = prompt.index(OPEN) + len(OPEN)
        end = prompt.index(CLOSE, start)
    except ValueError:
        return AllowlistParseResult(repos={}, fell_back=True)
    body = prompt[start:end].strip()
    if not body:
        return AllowlistParseResult(repos={}, fell_back=True)
    try:
        data = yaml.safe_load(body)
    except yaml.YAMLError:
        return AllowlistParseResult(repos={}, fell_back=True)
    if not isinstance(data, dict) or "repos" not in data:
        return AllowlistParseResult(repos={}, fell_back=True)
    raw = data["repos"] or {}
    if not isinstance(raw, dict):
        return AllowlistParseResult(repos={}, fell_back=True)
    out: dict[str, list[str]] = {}
    for k, v in raw.items():
        if not isinstance(v, list):
            continue
        out[str(k)] = [str(t) for t in v]
    return AllowlistParseResult(repos=out, fell_back=False)


def filter_bundle_for_repo(
    bundle_tasks: list[str],
    allowlist: AllowlistParseResult,
    repo_url: str,
    manifest_task_ids: set[str],
) -> tuple[list[str], list[str]]:
    """Return (tasks_to_run, warnings) for one repo in one bundle.

    Semantics:
      - fell_back → all bundle tasks.
      - repo absent from parsed map → all bundle tasks.
      - task id not in manifest → warn and drop.
      - intersection empty → [] (caller records `not-selected`).
    """
    warnings: list[str] = []
    if allowlist.fell_back or repo_url not in allowlist.repos:
        return list(bundle_tasks), warnings
    allowed = allowlist.repos[repo_url]
    cleaned = []
    for t in allowed:
        if t not in manifest_task_ids:
            warnings.append(f"unknown task id {t} for {repo_url}")
            continue
        cleaned.append(t)
    intersection = [t for t in bundle_tasks if t in cleaned]
    return intersection, warnings


# ---------------------------------------------------------------------------
# Parse-merge-rewrite of trigger prompts
# ---------------------------------------------------------------------------


def serialize_allowlist(repos: dict[str, list[str]]) -> str:
    """Deterministic YAML output matching what the skill should write."""
    if not repos:
        return f"{OPEN}\nrepos: {{}}\n{CLOSE}"
    lines = [OPEN, "repos:"]
    for url in sorted(repos):
        tasks = repos[url]
        task_list = ", ".join(tasks)
        lines.append(f"  {url}: [{task_list}]")
    lines.append(CLOSE)
    return "\n".join(lines)


def splice_allowlist(prompt: str, new_block: str) -> str:
    """Replace the existing delimited block, or append a new one if absent.

    Preserves the surrounding prompt text so hand-edits survive.
    """
    if OPEN in prompt and CLOSE in prompt:
        pattern = re.compile(
            re.escape(OPEN) + r".*?" + re.escape(CLOSE),
            re.DOTALL,
        )
        return pattern.sub(lambda m: new_block, prompt, count=1)
    sep = "\n\n" if not prompt.endswith("\n") else "\n"
    return prompt + sep + new_block + "\n"


def add_repo(prompt: str, repo: str, tasks: list[str]) -> str:
    parsed = parse_allowlist(prompt)
    repos = dict(parsed.repos)
    repos[repo] = list(tasks)
    return splice_allowlist(prompt, serialize_allowlist(repos))


def remove_repo(prompt: str, repo: str) -> str:
    parsed = parse_allowlist(prompt)
    repos = dict(parsed.repos)
    repos.pop(repo, None)
    return splice_allowlist(prompt, serialize_allowlist(repos))


def change_repo_tasks(prompt: str, repo: str, tasks: list[str]) -> str:
    """Replace a repo's task list. If tasks is empty, remove the repo."""
    if not tasks:
        return remove_repo(prompt, repo)
    parsed = parse_allowlist(prompt)
    repos = dict(parsed.repos)
    repos[repo] = list(tasks)
    return splice_allowlist(prompt, serialize_allowlist(repos))
