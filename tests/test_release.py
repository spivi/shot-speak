"""Release checks: the guides match the catalogue, generated files are fresh, nothing private is in the repo."""

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import catalog as C  # noqa: E402
import shotspeak as S  # noqa: E402

TEXT_SUFFIXES = {".md", ".py", ".json", ".txt", ".example", ""}


def repo_files():
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and not {".git", "__pycache__", "shotspeak_out"} & set(path.parts) and path.suffix in TEXT_SUFFIXES:
            yield path


def jpeg_segments(data):
    """The marker bytes of the segments before the picture data."""
    found, at = set(), 2
    while at + 4 <= len(data) and data[at] == 0xFF:
        marker = data[at + 1]
        found.add(marker)
        if marker == 0xDA:
            break
        at += 2 + int.from_bytes(data[at + 2:at + 4], "big")
    return found


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


class GeneratedFiles(unittest.TestCase):
    def check(self, script):
        done = subprocess.run([sys.executable, str(ROOT / "scripts" / script), "--check"], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, f"Run: python3 scripts/{script}\n{done.stdout}{done.stderr}")

    def test_generated_references_are_fresh(self):
        self.check("build_references.py")

    def test_examples_are_fresh(self):
        self.check("build_examples.py")

    def test_walkthrough_is_fresh(self):
        self.check("build_walkthrough.py")


class GuidesMatchCatalogue(unittest.TestCase):
    def test_skill_frontmatter(self):
        text = read("SKILL.md")
        match = re.match(r"---\nname: ([a-z0-9-]+)\ndescription: (.+)\n---\n", text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "shot-speak")
        self.assertLessEqual(len(match.group(2)), 1024)
        for phrase in ("swishy", "bullet time", "dramatic", "slo-mo", "AI-slop", "like that film", "Blender"):
            self.assertIn(phrase, match.group(2))

    def test_skill_and_readme_link_only_existing_references(self):
        text = read("SKILL.md")
        self.assertIn("references/index.md", text)
        self.assertIn("references/commands.md", text)
        for linked in re.findall(r"\]\((references/[^)#\s]+\.md)", text + read("README.md")):
            self.assertTrue((ROOT / linked).exists(), linked)

    def test_every_light_grade_and_speed_is_in_its_guide(self):
        for table, guide in ((C.LIGHTS, "references/light-colour/lighting.md"), (C.GRADES, "references/light-colour/grades.md"),
                             (C.SPEEDS, "references/camera/speed.md")):
            text = read(guide)
            for key, entry in table.items():
                self.assertIn(f"`{key}`", text, f"{key} is missing in {guide}")
                self.assertIn(entry["name"], text, f"{entry['name']} is missing in {guide}")

    def test_every_lens_is_in_the_lens_guide(self):
        text = read("references/camera/lens.md")
        for lens in C.LENSES:
            self.assertIn(f"| {lens} |", text)

    def test_every_avoid_clause_is_in_the_slop_guide(self):
        text = read("references/quality/avoid-clauses.md")
        for tell in C.SLOP_TELLS:
            if tell["avoid"]:
                self.assertIn(tell["avoid"], text, tell["id"])
        for heading, guide in (("## 1. Camera composition", "slop-camera-light"), ("## 2. Lighting", "slop-camera-light"),
                               ("## 3. Lens", "slop-lens-motion-finish"), ("## 4. Motion and speed", "slop-lens-motion-finish"),
                               ("## 5. Texture, colour and finish", "slop-lens-motion-finish"),
                               ("## The anti-slop check", "slop-overview")):
            self.assertIn(heading, read(f"references/quality/{guide}.md"))
        self.assertIn("## De-slop mode", read("references/flow/deslop.md"))

    def test_readme_states_the_defaults(self):
        text = read("README.md")
        self.assertIn(S.OPENAI_DEFAULT_MODEL, text)
        self.assertIn(f"{S.OPENAI_EST_USD_PER_IMAGE:.2f} USD", text)
        self.assertIn("SHOTSPEAK_OPENAI_MODEL", text)
        self.assertIn(f"{len(C.TECHNIQUES)} techniques", text)
        self.assertIn(f"{len(C.SLOP_TELLS)} AI-slop tells", text)
        self.assertIn(f"{len(C.LOOKS)} look recipes", text)
        self.assertIn(f"{len(C.SPEEDS)} speeds", text)
        self.assertIn(S.HIGGSFIELD_DEFAULT_MODEL, read("references/backends/higgsfield.md"))
        for section in ("## Why", "## Example: the same idea, 3 prompts, 3 real videos", "## Walkthrough: 1 session, step by step",
                        "## \"Like that film\"", "## When the look is not clear", "## Install", "## Quick start",
                        "## Blocking previs", "## Backends, cost and privacy", "## What is inside", "## The craft in 10 lines",
                        "## Further reading", "## Status", "## Contributing", "## License"):
            self.assertIn(section, text)

    def test_skill_states_the_spirit_and_the_four_gates(self):
        text = read("SKILL.md")
        spirit = text.split("## Spirit", 1)[1].split("## The usual path", 1)[0]
        for needle in ("enabler", "4 hard gates", "A clear yes before money is spent", "No names in a generator prompt",
                       "No user photos and no personal data", "Never print a key", "Fast paths", "shotspeak.py prompt"):
            self.assertIn(needle, spirit)
        self.assertLessEqual(len(text.splitlines()), 100)
        self.assertLessEqual(len(re.findall(r"\b(must|MUST)\b", text)), 2)
        commands = read("references/commands.md")
        for command in S.COMMANDS:
            self.assertIn(f"shotspeak.py {command}", commands, command)
        self.assertIn("image_gen", read("references/flow/mock-stills.md"))

    def test_readme_names_every_reference_site(self):
        text = read("README.md").split("## Further reading", 1)[1].split("## Status", 1)[0]
        for name in ("ShotDeck", "Frameset", "Stills Lab", "Film-Grab", "StudioBinder", "American Cinematographer", "MovieNet",
                     "CineScale", "CineTechBench"):
            self.assertIn(name, text)
        self.assertIn("Do not copy a still", text)

    def test_license_is_mit(self):
        self.assertTrue(read("LICENSE").startswith("MIT License"))


class Hygiene(unittest.TestCase):
    def test_no_secret_no_private_path_no_email(self):
        patterns = {
            "a home folder path": re.compile(r"/Users/(?!someone/|\|)[A-Za-z0-9_.-]+/|/home/(?!\|)[A-Za-z0-9_.-]+/"),
            "an email address": re.compile(r"[\w.+-]+@(?!example\.org)[\w-]+\.[a-z]{2,}"),
            "a key": re.compile(r"\b(sk|r8|fal)[-_](?!test-|x\b|k\b|from|secret_value)[A-Za-z0-9_-]{20,}"),
        }
        for path in repo_files():
            text = path.read_text(encoding="utf-8", errors="replace")
            for what, pattern in patterns.items():
                found = pattern.search(text)
                self.assertIsNone(found, f"{path.relative_to(ROOT)} contains {what}: {found.group(0) if found else ''}")

    def test_only_small_known_images_and_no_env_file_in_the_repo(self):
        """PNG only for example previs stills. JPEG only for the README image slots and the video posters.
        MP4 and 1 GIF only for the README videos in docs/video/. No other video, no scene file."""
        for path in ROOT.rglob("*"):
            if ".git" in path.parts or "shotspeak_out" in path.parts:
                continue
            rel = path.relative_to(ROOT).as_posix()
            if path.suffix.lower() == ".png":
                allowed = re.fullmatch(r"examples/[a-z0-9-]+/previs/option_[A-D]/(still_(start|mid|end)|plan_overhead)\.png", rel)

                self.assertTrue(allowed, rel)
                self.assertLess(path.stat().st_size, 200_000, rel)
                continue
            if path.suffix.lower() == ".jpg":  # JPEG only for the README image slots and video posters: small, and with no metadata
                self.assertTrue(re.fullmatch(r"docs/img/(thumb/)?[a-z0-9-]+_(bad|plain|skill|option_[A-D])\.jpg", rel)
                                or re.fullmatch(r"docs/video/[a-z0-9-]+/[1-3]_(noob|plain|skill)\.jpg", rel), rel)
                self.assertLess(path.stat().st_size, 300_000, rel)
                data = path.read_bytes()
                self.assertEqual(data[:3], b"\xff\xd8\xff", rel)
                for mark in (b"Exif", b"http://ns.adobe.com", b"ICC_PROFILE", b"Photoshop", b"/Users/", b"/home/", b"GPS"):
                    self.assertNotIn(mark, data, f"{rel} holds {mark!r}")
                self.assertEqual(jpeg_segments(data) & {0xE1, 0xE2, 0xED, 0xFE}, set(), f"{rel} has a metadata segment")
                continue
            if path.suffix.lower() == ".mp4":  # the README videos: small, and with no metadata
                self.assertTrue(re.fullmatch(r"docs/video/[a-z0-9-]+/[1-3]_(noob|plain|skill)\.mp4", rel), rel)
                self.assertLess(path.stat().st_size, 3_000_000, rel)
                data = path.read_bytes()
                self.assertEqual(data[4:8], b"ftyp", rel)
                for mark in (b"/Users/", b"/home/", b"\xa9too", b"\xa9nam", b"\xa9day", b"com.apple", b"creation_time"):
                    self.assertNotIn(mark, data, f"{rel} holds {mark!r}")
                continue
            if path.suffix.lower() == ".gif":  # the README comparison: 1 file, under 6 MB, with no comment and no metadata
                self.assertEqual(rel, "docs/video/bike-cliff/compare.gif")
                self.assertLess(path.stat().st_size, 6_000_000, rel)
                data = path.read_bytes()
                self.assertEqual(data[:6], b"GIF89a", rel)
                self.assertEqual(data[:1024].count(b"\x21\xfe"), 0, f"{rel} has a comment block")
                self.assertNotIn(b"/Users/", data, rel)
                continue
            self.assertNotIn(path.suffix.lower(), {".jpeg", ".webp", ".mov", ".blend", ".blend1"}, path)

    def test_image_receipts_match_the_committed_files(self):
        path = ROOT / "docs" / "img" / "receipts.json"
        if not path.is_file():
            self.skipTest("no comparison images yet")
        text = path.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"sk-[A-Za-z0-9_-]{20,}|Bearer ")
        for receipt in json.loads(text):
            if receipt.get("status") != "ok":
                continue
            self.assertTrue(receipt["file"].endswith(".jpg"), receipt["file"])
            self.assertRegex(receipt["image_sha256"], r"^[0-9a-f]{64}$")       # the provider's PNG
            self.assertEqual(receipt["file_sha256"], S.P.sha256_file(path.parent / receipt["file"]), receipt["file"])
            self.assertNotEqual(receipt["file_sha256"], receipt["image_sha256"])
            self.assertFalse(path.name in {".env", ".env.local"}, path)

    def test_video_receipts_match_the_committed_files(self):
        for path in sorted((ROOT / "docs" / "video").glob("*/receipts.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(doc["videos"]), 3, path)
            for receipt in doc["videos"]:
                for key in ("source_file", "source_sha256", "file_sha256", "model", "duration_s", "resolution", "takes",
                            "prompt_file_sha256"):
                    self.assertIn(key, receipt, f"{path.relative_to(ROOT)}: {key}")
                self.assertEqual(receipt["file_sha256"], S.P.sha256_file(path.parent / receipt["file"]), receipt["file"])
                self.assertEqual(receipt["poster_sha256"], S.P.sha256_file(path.parent / receipt["poster"]), receipt["poster"])
                self.assertEqual(receipt["prompt_file_committed_sha256"], S.P.sha256_file(ROOT / receipt["prompt_file_committed"]))
                self.assertRegex(receipt["source_sha256"], r"^[0-9a-f]{64}$")
                self.assertRegex(receipt["prompt_file_sha256"], r"^[0-9a-f]{64}$")
                self.assertNotIn("/", receipt["source_file"])
                self.assertNotEqual(receipt["file_sha256"], receipt["source_sha256"])
                self.assertEqual((receipt["duration_s"], receipt["resolution"], receipt["takes"]), (10, "480p", 1))
            compare = doc["compare"]
            self.assertEqual(compare["file_sha256"], S.P.sha256_file(path.parent / compare["file"]))
            self.assertEqual(compare["file_bytes"], (path.parent / compare["file"]).stat().st_size)
            self.assertEqual(compare["made_from"], [v["file"] for v in doc["videos"]])
            self.assertIn("ffmpeg", compare["encode"])
            self.assertIn("build_compare_gif.sh", compare["reproduce"])

    def test_readme_video_section_links_every_video_and_poster(self):
        text = read("README.md")
        self.assertIn("(docs/video/bike-cliff/compare.gif)", text)
        for name in ("1_noob", "2_plain", "3_skill"):
            self.assertIn(f"(docs/video/bike-cliff/{name}.jpg)](docs/video/bike-cliff/{name}.mp4)", text)
        self.assertIn("examples/bike-cliff/", text)
        for slug in ("dog-bullet-time", "skate-kickflip", "alley-fight", "birthday-candles"):
            self.assertIn(f"](examples/{slug}/)", text)
            self.assertTrue((ROOT / "examples" / slug).is_dir(), slug)

    def test_example_previs_stills_hold_no_machine_data(self):
        """A PNG from Blender can carry the file name, the host and the date. The script turns that off."""
        for path in sorted(ROOT.glob("examples/*/previs/option_*/*.png")):
            data = path.read_bytes()
            for chunk in (b"tEXt", b"iTXt", b"zTXt", b"/Users/", b"/home/", b"tIME"):
                self.assertNotIn(chunk, data, f"{path.relative_to(ROOT)} holds {chunk!r}")
        for path in sorted(ROOT.glob("examples/*/previs/previs.json")):
            manifest = json.loads(path.read_text(encoding="utf-8"))
            for entry in manifest["options"]:
                for item in entry["files"]:
                    self.assertFalse(Path(item["path"]).is_absolute())
                    self.assertEqual(S.P.sha256_file(path.parent / item["path"]), item["sha256"], item["path"])

    def test_env_files_are_ignored(self):
        ignore = read(".gitignore")
        for line in (".env", ".env.*", "shotspeak_out/"):
            self.assertIn(line, ignore.splitlines())

    @unittest.skipUnless(hasattr(sys, "stdlib_module_names"), "needs Python 3.10 or later")
    def test_scripts_use_the_standard_library_only(self):
        own = {path.stem for path in (ROOT / "scripts").glob("*.py")}
        # blender_blocking.py runs inside Blender. It is the only file that can use Blender's own modules.
        inside_blender = {"bpy", "bmesh", "mathutils"}
        for path in (ROOT / "scripts").glob("*.py"):
            allowed = set(sys.stdlib_module_names) | own | (inside_blender if path.name == "blender_blocking.py" else set())
            for module in re.findall(r"^(?:import|from) ([a-zA-Z_][\w]*)", path.read_text(encoding="utf-8"), re.M):
                self.assertIn(module, allowed, f"{path.name} imports {module}")
        self.assertNotRegex((ROOT / "scripts" / "previs.py").read_text(encoding="utf-8"), r"^(import|from) (bpy|bmesh|mathutils)")


if __name__ == "__main__":
    unittest.main()
