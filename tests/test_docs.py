"""Doc layout checks: small files, working links, an index tree with no orphans."""

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_references as B  # noqa: E402

MAX_LINES = 100
LINK = re.compile(r"\]\(([^)#\s]+\.md)(?:#[^)]*)?\)")
# README.md is the GitHub landing page and CHANGELOG.md is a log. The scene files in examples/ are tool output.
OUT_OF_SCOPE_NAMES = {"README.md", "CHANGELOG.md"}
TOOL_OUTPUT = {"options.md", "final_spec.md", "sequence.md"}


def markdown_files():
    for path in sorted(ROOT.rglob("*.md")):
        parts = set(path.relative_to(ROOT).parts)
        if {".git", "shotspeak_out", "__pycache__"} & parts:
            continue
        yield path


def in_scope(path):
    rel = path.relative_to(ROOT)
    if rel.parent == Path(".") and path.name in OUT_OF_SCOPE_NAMES:
        return False
    return not (rel.parts[0] == "examples" and path.name in TOOL_OUTPUT)


def links(path):
    """The relative .md targets of a file, resolved. External links are skipped."""
    found = []
    for target in LINK.findall(path.read_text(encoding="utf-8")):
        if "://" not in target:
            found.append((target, (path.parent / target).resolve()))
    return found


def reference_files():
    return [p for p in markdown_files() if p.relative_to(ROOT).parts[0] == "references"]


class SmallFiles(unittest.TestCase):
    def test_every_in_scope_markdown_file_has_100_lines_or_fewer(self):
        for path in markdown_files():
            if in_scope(path):
                count = len(path.read_text(encoding="utf-8").splitlines())
                self.assertLessEqual(count, MAX_LINES, f"{path.relative_to(ROOT)} has {count} lines")


class Links(unittest.TestCase):
    def test_every_relative_markdown_link_resolves(self):
        sources = [ROOT / "SKILL.md", ROOT / "README.md"] + reference_files() + [
            p for p in markdown_files() if p.relative_to(ROOT).parts[0] == "examples" and in_scope(p)]
        for path in sources:
            for target, resolved in links(path):
                self.assertTrue(resolved.is_file(), f"{path.relative_to(ROOT)} links to {target}, which does not exist")

    def test_every_reference_file_is_reachable_from_skill_md(self):
        seen, queue = set(), [(ROOT / "SKILL.md").resolve()]
        while queue:
            path = queue.pop()
            if path in seen:
                continue
            seen.add(path)
            queue += [resolved for _, resolved in links(path) if resolved.is_file()]
        orphans = [p.relative_to(ROOT).as_posix() for p in reference_files() if p.resolve() not in seen]
        self.assertEqual(orphans, [], f"not reachable from SKILL.md: {orphans}")


class Indexes(unittest.TestCase):
    def test_every_references_folder_with_files_has_an_index(self):
        folders = {p.parent for p in reference_files()}
        for folder in folders:
            self.assertTrue((folder / "index.md").is_file(), f"{folder.relative_to(ROOT)} has no index.md")

    def test_every_index_links_its_children_and_its_child_indexes(self):
        indexes = [p for p in markdown_files() if p.name == "index.md" and p.relative_to(ROOT).parts[0] in {"references", "examples"}]
        self.assertGreaterEqual(len(indexes), 10)
        for index in indexes:
            linked = {resolved for _, resolved in links(index)}
            for child in sorted(index.parent.glob("*.md")):
                if child.name != "index.md" and not (child.name in TOOL_OUTPUT):
                    self.assertIn(child.resolve(), linked, f"{index.relative_to(ROOT)} does not link {child.name}")
            for folder in sorted(p for p in index.parent.iterdir() if p.is_dir()):
                if (folder / "index.md").is_file():
                    self.assertIn((folder / "index.md").resolve(), linked,
                                  f"{index.relative_to(ROOT)} does not link {folder.name}/index.md")

    def test_every_index_line_says_when_to_read_it(self):
        for index in (p for p in reference_files() if p.name == "index.md" and p.parent.name != "references"):
            body = index.read_text(encoding="utf-8").split("## See also")[0]
            for line in body.splitlines():
                if line.startswith("- ["):
                    self.assertIn("Read ", line, f"{index.relative_to(ROOT)}: {line[:60]}")

    def test_every_child_has_a_heading_and_a_see_also_list(self):
        for path in reference_files():
            if path.name == "index.md":
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertTrue(lines[0].startswith("# "), path)
            self.assertIn("## See also", lines, f"{path.relative_to(ROOT)} has no See also list")


class GeneratedLayout(unittest.TestCase):
    def test_a_left_over_generated_file_makes_the_check_fail(self):
        stray = ROOT / "references" / "camera" / "old-camera-moves.md"
        stray.write_text(B.NOTE + "\n", encoding="utf-8")
        try:
            done = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_references.py"), "--check"],
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, 1)
            self.assertIn("old-camera-moves.md", done.stdout)
        finally:
            stray.unlink()

    def test_no_generated_file_is_longer_than_the_limit(self):
        files = B.build_all()
        self.assertGreaterEqual(len(files), 17)
        for rel, text in files.items():
            self.assertLessEqual(len(text.splitlines()), MAX_LINES, rel)


if __name__ == "__main__":
    unittest.main()
