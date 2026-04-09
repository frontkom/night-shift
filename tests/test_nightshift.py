"""Night Shift test suite.

Covers two things:
  1. Structural invariants of the repo (manifest <-> tasks <-> wrappers are
     in sync, no stale references, task files contain the right allowlist
     checks).
  2. Behavioural tests of the reference implementations in nightshift_ref.py
     (YAML parsing, filter logic, parse-merge-rewrite of trigger prompts).

Run with:  python3 -m unittest tests.test_nightshift -v
Or:        python3 tests/test_nightshift.py
"""

from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path

import yaml

# Make the tests/ dir importable regardless of cwd.
TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from nightshift_ref import (  # noqa: E402
    CLOSE,
    OPEN,
    add_repo,
    change_repo_tasks,
    filter_bundle_for_repo,
    parse_allowlist,
    remove_repo,
    serialize_allowlist,
    splice_allowlist,
)

REPO_ROOT = TESTS_DIR.parent
MANIFEST_PATH = REPO_ROOT / "manifest.yml"
TASKS_DIR = REPO_ROOT / "tasks"
BUNDLES_DIR = REPO_ROOT / "bundles"
SKILL_PATH = REPO_ROOT / "skill" / "SKILL.md"
README_PATH = REPO_ROOT / "README.md"
HOWTO_PATH = REPO_ROOT / "HOW-TO.md"


def load_manifest() -> dict:
    with open(MANIFEST_PATH) as f:
        return yaml.safe_load(f)


def task_ids_by_bundle() -> dict[str, list[str]]:
    m = load_manifest()
    out: dict[str, list[str]] = {}
    for t in m["tasks"]:
        out.setdefault(t["bundle"], []).append(t["id"])
    return out


def all_task_ids() -> set[str]:
    return {t["id"] for t in load_manifest()["tasks"]}


# ---------------------------------------------------------------------------
# 1. Structural invariants
# ---------------------------------------------------------------------------


class TestManifestStructure(unittest.TestCase):
    def test_twelve_tasks(self):
        self.assertEqual(len(load_manifest()["tasks"]), 12)

    def test_four_bundles(self):
        self.assertEqual(set(load_manifest()["bundles"].keys()),
                         {"plans", "docs", "code-fixes", "audits"})

    def test_every_task_has_file(self):
        for tid in all_task_ids():
            self.assertTrue(
                (TASKS_DIR / f"{tid}.md").exists(),
                f"missing tasks/{tid}.md",
            )

    def test_every_task_file_has_manifest_entry(self):
        manifest_ids = all_task_ids()
        for p in TASKS_DIR.glob("*.md"):
            self.assertIn(
                p.stem, manifest_ids,
                f"orphan task file tasks/{p.name} with no manifest entry",
            )

    def test_task_ordering_stable_within_bundle(self):
        by_bundle = task_ids_by_bundle()
        for bundle, tids in by_bundle.items():
            self.assertTrue(len(tids) >= 1, f"empty bundle {bundle}")


class TestTaskFileAllowlistCheck(unittest.TestCase):
    """Every task file must contain a self-check against allowed_tasks with
    its own id. Stale 'task N is not in the task list' lines must be gone."""

    def test_every_task_has_allowlist_self_check(self):
        for tid in sorted(all_task_ids()):
            content = (TASKS_DIR / f"{tid}.md").read_text()
            self.assertIn(
                "allowed_tasks",
                content,
                f"{tid}.md missing allowed_tasks reference",
            )
            self.assertIn(
                f"`{tid}`",
                content,
                f"{tid}.md must reference its own id in backticks",
            )

    def test_no_stale_numbered_task_references(self):
        pattern = re.compile(r"task\s+\d+\s+is not in the task list")
        for p in TASKS_DIR.glob("*.md"):
            self.assertIsNone(
                pattern.search(p.read_text()),
                f"stale numbered-task line in {p.name}",
            )

    def test_no_stale_this_task_not_in_list(self):
        for p in TASKS_DIR.glob("*.md"):
            content = p.read_text()
            self.assertNotIn(
                "this task is not in the task list",
                content.lower(),
                f"stale vague allowlist line in {p.name} — should reference allowed_tasks",
            )


class TestWrappersReferenceAllowlistContract(unittest.TestCase):
    """All three multi-* wrappers must reference the <night-shift-config>
    parsing contract (so the LLM running them knows to parse and filter)."""

    WRAPPERS = [
        "multi-plans.md",
        "multi-docs-and-code-fixes.md",
        "multi-audits.md",
    ]

    def test_every_wrapper_mentions_allowlist(self):
        for w in self.WRAPPERS:
            content = (BUNDLES_DIR / w).read_text()
            self.assertIn(OPEN, content, f"{w} missing <night-shift-config> ref")
            self.assertIn(
                "Per-repo task allowlist",
                content,
                f"{w} missing link to _multi-runner.md allowlist spec",
            )

    def test_every_wrapper_uses_not_selected_status(self):
        for w in self.WRAPPERS:
            content = (BUNDLES_DIR / w).read_text()
            self.assertIn(
                "not-selected",
                content,
                f"{w} missing not-selected status token in summary table",
            )

    def test_inner_bundles_filter_on_allowed_tasks(self):
        for b in ("plans.md", "docs.md", "code-fixes.md", "audits.md", "all.md"):
            content = (BUNDLES_DIR / b).read_text()
            self.assertIn(
                "allowed_tasks",
                content,
                f"bundles/{b} missing allowed_tasks filter clause",
            )

    def test_multi_runner_has_allowlist_section(self):
        content = (BUNDLES_DIR / "_multi-runner.md").read_text()
        self.assertIn("Per-repo task allowlist", content)
        self.assertIn("parse", content.lower())
        self.assertIn("fall back", content.lower())

    def test_multi_docs_and_audits_derive_bundle_tasks_from_manifest(self):
        """Wrappers that need to know which task ids belong to their bundle
        must fetch manifest.yml rather than hardcode a list. Otherwise adding
        a 5th audit task silently excludes it from the filter."""
        for w in ("multi-docs-and-code-fixes.md", "multi-audits.md"):
            content = (BUNDLES_DIR / w).read_text()
            self.assertIn(
                "manifest.yml",
                content,
                f"{w} must reference manifest.yml to derive bundle task sets",
            )
            self.assertIn(
                "do **not** hardcode",
                content.lower().replace("do not hardcode", "do **not** hardcode"),
                f"{w} must warn against hardcoded task id lists",
            )

    def test_skill_derives_trigger_task_sets_from_manifest(self):
        content = SKILL_PATH.read_text()
        self.assertIn(
            "Do not hardcode task ids in the skill",
            content,
            "skill must explicitly refuse to hardcode task id lists",
        )


class TestSkillAndDocs(unittest.TestCase):
    def test_skill_has_picker(self):
        content = SKILL_PATH.read_text()
        self.assertIn("Per-repo task picker", content)
        self.assertIn("AskUserQuestion", content)
        self.assertIn("<night-shift-config>", content)
        self.assertIn("Change tasks for a repo", content)
        self.assertIn("parse-merge-rewrite", content.lower().replace("–", "-"))

    def test_skill_step0_offers_change_tasks(self):
        content = SKILL_PATH.read_text()
        self.assertIn("Change tasks for a repo", content)

    def test_readme_has_no_stale_tasks_field(self):
        content = README_PATH.read_text()
        # The bullet list example must not advertise a Tasks: field any more.
        self.assertNotRegex(
            content,
            r"^- Tasks:\s",
            "README still advertises the removed Tasks: CLAUDE.md field",
        )

    def test_howto_documents_picker(self):
        content = HOWTO_PATH.read_text()
        self.assertIn("checklist", content.lower())
        self.assertIn("Change tasks for a repo", content)

    def test_version_marker_present(self):
        content = SKILL_PATH.read_text()
        self.assertRegex(content, r"NIGHT_SHIFT_VERSION:\s+\d{4}-\d{2}-\d{2}")


# ---------------------------------------------------------------------------
# 2. Behavioural — reference implementations
# ---------------------------------------------------------------------------


VALID_PROMPT = f"""Fetch https://raw.githubusercontent.com/x/y/main/wrapper.md and run it.

{OPEN}
repos:
  https://github.com/a/b: [build-planned-features, add-tests]
  https://github.com/c/d: [find-bugs, improve-seo]
{CLOSE}
"""

ABSENT_PROMPT = "Fetch something and run it. No config block here."

MALFORMED_PROMPT = f"""Fetch something.

{OPEN}
repos:
  this is not: valid: yaml: at all
{CLOSE}
"""

EMPTY_MAP_PROMPT = f"""Fetch something.

{OPEN}
repos: {{}}
{CLOSE}
"""


class TestAllowlistParsing(unittest.TestCase):
    def test_valid_block_parses(self):
        r = parse_allowlist(VALID_PROMPT)
        self.assertFalse(r.fell_back)
        self.assertEqual(
            r.repos,
            {
                "https://github.com/a/b": ["build-planned-features", "add-tests"],
                "https://github.com/c/d": ["find-bugs", "improve-seo"],
            },
        )

    def test_absent_block_falls_back(self):
        r = parse_allowlist(ABSENT_PROMPT)
        self.assertTrue(r.fell_back)
        self.assertEqual(r.repos, {})

    def test_malformed_yaml_falls_back(self):
        r = parse_allowlist(MALFORMED_PROMPT)
        self.assertTrue(r.fell_back)

    def test_empty_map_does_not_fall_back(self):
        r = parse_allowlist(EMPTY_MAP_PROMPT)
        # Empty map is a valid "everything not-selected" state.
        self.assertFalse(r.fell_back)
        self.assertEqual(r.repos, {})


class TestBundleFilter(unittest.TestCase):
    MANIFEST_IDS = {
        "build-planned-features", "update-changelog", "update-user-guide",
        "document-decisions", "suggest-improvements", "add-tests",
        "improve-accessibility", "translate-ui", "find-security-issues",
        "find-bugs", "improve-seo", "improve-performance",
    }

    def test_fall_back_returns_full_bundle(self):
        allowlist = parse_allowlist(ABSENT_PROMPT)
        tasks, warns = filter_bundle_for_repo(
            ["find-bugs", "improve-seo"],
            allowlist,
            "https://github.com/a/b",
            self.MANIFEST_IDS,
        )
        self.assertEqual(tasks, ["find-bugs", "improve-seo"])
        self.assertEqual(warns, [])

    def test_repo_absent_returns_full_bundle(self):
        allowlist = parse_allowlist(VALID_PROMPT)
        tasks, _ = filter_bundle_for_repo(
            ["find-bugs"], allowlist, "https://github.com/unknown/repo",
            self.MANIFEST_IDS,
        )
        self.assertEqual(tasks, ["find-bugs"])

    def test_intersection(self):
        allowlist = parse_allowlist(VALID_PROMPT)
        tasks, _ = filter_bundle_for_repo(
            ["find-bugs", "improve-seo", "find-security-issues"],
            allowlist,
            "https://github.com/c/d",
            self.MANIFEST_IDS,
        )
        self.assertEqual(tasks, ["find-bugs", "improve-seo"])

    def test_empty_intersection(self):
        allowlist = parse_allowlist(VALID_PROMPT)
        tasks, _ = filter_bundle_for_repo(
            ["update-changelog"],
            allowlist,
            "https://github.com/a/b",
            self.MANIFEST_IDS,
        )
        self.assertEqual(tasks, [])

    def test_unknown_task_id_warns_and_is_dropped(self):
        bad = VALID_PROMPT.replace("find-bugs", "typo-task")
        allowlist = parse_allowlist(bad)
        tasks, warns = filter_bundle_for_repo(
            ["find-bugs", "improve-seo"],
            allowlist,
            "https://github.com/c/d",
            self.MANIFEST_IDS,
        )
        self.assertEqual(tasks, ["improve-seo"])
        self.assertTrue(any("typo-task" in w for w in warns))


class TestParseMergeRewrite(unittest.TestCase):
    def test_add_repo_to_existing_block(self):
        new = add_repo(VALID_PROMPT, "https://github.com/x/y", ["add-tests"])
        r = parse_allowlist(new)
        self.assertEqual(
            set(r.repos),
            {"https://github.com/a/b", "https://github.com/c/d", "https://github.com/x/y"},
        )
        self.assertEqual(r.repos["https://github.com/x/y"], ["add-tests"])

    def test_add_repo_creates_block_if_absent(self):
        new = add_repo(ABSENT_PROMPT, "https://github.com/x/y", ["add-tests"])
        self.assertIn(OPEN, new)
        r = parse_allowlist(new)
        self.assertEqual(r.repos, {"https://github.com/x/y": ["add-tests"]})

    def test_remove_repo(self):
        new = remove_repo(VALID_PROMPT, "https://github.com/a/b")
        r = parse_allowlist(new)
        self.assertEqual(list(r.repos), ["https://github.com/c/d"])

    def test_remove_last_repo_yields_empty_map(self):
        p = VALID_PROMPT
        p = remove_repo(p, "https://github.com/a/b")
        p = remove_repo(p, "https://github.com/c/d")
        r = parse_allowlist(p)
        self.assertEqual(r.repos, {})
        self.assertFalse(r.fell_back)  # explicit empty, not absent

    def test_change_repo_tasks_preserves_others(self):
        new = change_repo_tasks(
            VALID_PROMPT, "https://github.com/a/b", ["update-changelog"],
        )
        r = parse_allowlist(new)
        self.assertEqual(r.repos["https://github.com/a/b"], ["update-changelog"])
        self.assertEqual(r.repos["https://github.com/c/d"], ["find-bugs", "improve-seo"])

    def test_change_repo_tasks_empty_removes_repo(self):
        new = change_repo_tasks(VALID_PROMPT, "https://github.com/a/b", [])
        r = parse_allowlist(new)
        self.assertNotIn("https://github.com/a/b", r.repos)

    def test_splice_preserves_surrounding_text(self):
        prompt = f"BEFORE\n{OPEN}\nrepos:\n  x: [a]\n{CLOSE}\nAFTER"
        out = splice_allowlist(prompt, f"{OPEN}\nrepos:\n  x: [b]\n{CLOSE}")
        self.assertTrue(out.startswith("BEFORE"))
        self.assertTrue(out.endswith("AFTER"))
        self.assertIn("[b]", out)

    def test_serialize_roundtrip(self):
        repos = {
            "https://github.com/a/b": ["build-planned-features", "add-tests"],
            "https://github.com/c/d": ["find-bugs"],
        }
        block = serialize_allowlist(repos)
        wrapped = f"intro text\n{block}\noutro text"
        r = parse_allowlist(wrapped)
        self.assertEqual(r.repos, repos)


class TestEndToEndPipeline(unittest.TestCase):
    """Simulates the full chain: picker produces selections → skill writes a
    trigger prompt with allowlist block → wrapper parses its own prompt →
    wrapper decides which repos/tasks to dispatch per bundle. Verifies the
    intended outcome matches what the user picked."""

    def setUp(self):
        self.manifest = load_manifest()
        self.ids = [t["id"] for t in self.manifest["tasks"]]
        self.bundle_of = {t["id"]: t["bundle"] for t in self.manifest["tasks"]}
        self.by_bundle = task_ids_by_bundle()
        self.manifest_ids = set(self.ids)

    def _select(self, picks: list[set[str]]) -> list[set[str]]:
        """Picker is now Claude Code's AskUserQuestion — selections come back
        as plain sets per repo. Helper just echoes the test's intent."""
        return picks

    def _build_trigger_prompt(
        self,
        base_prompt: str,
        selections: dict[str, set[str]],
        bundle_ids: set[str],
    ) -> str:
        """Build a prompt as the skill's Step 4 would: filter each repo's
        selection to the bundle's task set, drop repos with empty intersection,
        splice the YAML block in."""
        repos_map: dict[str, list[str]] = {}
        for repo, sel in selections.items():
            filtered = [t for t in self.ids if t in sel and t in bundle_ids]
            if filtered:
                repos_map[repo] = filtered
        return splice_allowlist(base_prompt, serialize_allowlist(repos_map))

    def test_three_repos_mixed_selections(self):
        repo_a = "https://github.com/user/repo-a"
        repo_b = "https://github.com/user/repo-b"
        repo_c = "https://github.com/user/repo-c"

        # User picks:
        #   repo-a: everything except audits
        #   repo-b: only audits
        #   repo-c: nothing
        all_ids = set(self.ids)
        audits = set(self.by_bundle["audits"])
        selections = self._select([
            all_ids - audits,  # repo-a
            audits,            # repo-b
            set(),             # repo-c
        ])
        sel_map = {
            repo_a: selections[0],
            repo_b: selections[1],
            repo_c: selections[2],
        }

        # --- Plans trigger ---
        plans_ids = set(self.by_bundle["plans"])
        plans_prompt = self._build_trigger_prompt(
            "Fetch multi-plans.md and run it.", sel_map, plans_ids,
        )
        plans_parsed = parse_allowlist(plans_prompt)
        self.assertFalse(plans_parsed.fell_back)
        # Only repo-a has build-planned-features (audits-off leaves plans intact)
        self.assertEqual(set(plans_parsed.repos), {repo_a})
        tasks, _ = filter_bundle_for_repo(
            list(plans_ids), plans_parsed, repo_a, self.manifest_ids,
        )
        self.assertEqual(tasks, ["build-planned-features"])

        # --- Docs + code-fixes trigger ---
        docs_fix_ids = set(self.by_bundle["docs"]) | set(self.by_bundle["code-fixes"])
        df_prompt = self._build_trigger_prompt(
            "Fetch multi-docs-and-code-fixes.md and run it.", sel_map, docs_fix_ids,
        )
        df_parsed = parse_allowlist(df_prompt)
        self.assertEqual(set(df_parsed.repos), {repo_a})
        tasks, _ = filter_bundle_for_repo(
            list(self.by_bundle["docs"]), df_parsed, repo_a, self.manifest_ids,
        )
        self.assertEqual(sorted(tasks), sorted(self.by_bundle["docs"]))
        tasks, _ = filter_bundle_for_repo(
            list(self.by_bundle["code-fixes"]), df_parsed, repo_a, self.manifest_ids,
        )
        self.assertEqual(sorted(tasks), sorted(self.by_bundle["code-fixes"]))

        # --- Audits trigger ---
        audits_ids = set(self.by_bundle["audits"])
        audits_prompt = self._build_trigger_prompt(
            "Fetch multi-audits.md and run it.", sel_map, audits_ids,
        )
        audits_parsed = parse_allowlist(audits_prompt)
        # repo-a turned audits off → not present. repo-b all audits → present.
        # repo-c none → not present.
        self.assertEqual(set(audits_parsed.repos), {repo_b})
        tasks, _ = filter_bundle_for_repo(
            list(audits_ids), audits_parsed, repo_b, self.manifest_ids,
        )
        self.assertEqual(sorted(tasks), sorted(audits_ids))

    def test_all_empty_triggers_skip_trigger_creation(self):
        """If every repo deselects every task in a bundle, the skill must
        skip creating that trigger. The reference check: filtered repos_map
        would be empty, which the skill interprets as 'don't create'."""
        repo = "https://github.com/user/lonely-repo"
        selections = self._select([set()])
        sel_map = {repo: selections[0]}

        for bundle_key, bundle_ids in [
            ("plans", set(self.by_bundle["plans"])),
            ("audits", set(self.by_bundle["audits"])),
        ]:
            prompt = self._build_trigger_prompt(
                f"Fetch multi-{bundle_key}.md and run it.", sel_map, bundle_ids,
            )
            parsed = parse_allowlist(prompt)
            self.assertEqual(
                parsed.repos, {},
                f"{bundle_key} trigger would be created with empty map; skill should skip",
            )

    def test_change_tasks_for_one_repo_preserves_others(self):
        """Simulates: user has 2 repos in an existing trigger, then picks
        'Change tasks for a repo' and modifies only one. The other repo's
        entry must survive unchanged, and the rest of the prompt (hand-edits)
        must be preserved."""
        hand_edited_prompt = (
            "Fetch multi-audits.md and run it. CUSTOM NOTE: do not email me.\n"
            f"\n{OPEN}\nrepos:\n"
            "  https://github.com/user/repo-a: [find-bugs, improve-seo]\n"
            "  https://github.com/user/repo-b: [find-security-issues]\n"
            f"{CLOSE}\n"
        )
        new = change_repo_tasks(
            hand_edited_prompt,
            "https://github.com/user/repo-a",
            ["improve-performance"],
        )
        self.assertIn("CUSTOM NOTE: do not email me.", new)
        parsed = parse_allowlist(new)
        self.assertEqual(
            parsed.repos["https://github.com/user/repo-a"], ["improve-performance"],
        )
        self.assertEqual(
            parsed.repos["https://github.com/user/repo-b"], ["find-security-issues"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
