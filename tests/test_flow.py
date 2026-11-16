"""Offline tests for 0.2.0: look recipes, references, rounds, the lock, the fast path, image import, routing,
sequences, and the generated walkthrough. No test may reach the network."""

import io
import json
import re
import socket
import sys
import tempfile
import unittest
import urllib.request
import xml.etree.ElementTree as ET
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_images  # noqa: E402
import catalog as C  # noqa: E402
import shotspeak as S  # noqa: E402
from support import PNG, run  # noqa: E402

HF_KEY = "hfid-0000:hfsecret-THISISAFAKEKEY123456"


class Offline(unittest.TestCase):
    def setUp(self):
        self._urlopen, self._connect = urllib.request.urlopen, socket.create_connection

        def bomb(*args, **kwargs):
            raise AssertionError("A test tried to reach the network.")

        urllib.request.urlopen = bomb
        socket.create_connection = bomb
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        urllib.request.urlopen, socket.create_connection = self._urlopen, self._connect
        self.tmp.cleanup()

    def base(self, *extra):
        return ["--cwd", str(self.dir), *extra]

    def plan(self, phrase, name="run", **kw):
        out = self.dir / name
        argv = ["plan", "--phrase", phrase, "--out", str(out)]
        for key, value in kw.items():
            argv += [f"--{key}", value]
        code, text, err = run(self.base(*argv))
        self.assertIn(code, (0, 3), err)
        return out, text

    def all_text(self, folder):
        return "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in sorted(Path(folder).rglob("*")) if p.is_file())


def word(name):
    return re.compile(r"(?<![a-z0-9])" + re.escape(name) + r"(?![a-z0-9])", re.I)


class LookRecipes(Offline):
    def test_every_recipe_is_complete_and_name_free(self):
        self.assertGreaterEqual(len(C.LOOKS), 30)
        self.assertEqual(set(C.LOOKS), set(S.LOOK_ALIASES))
        for look_id, look in C.LOOKS.items():
            self.assertIn(look["technique"], C.TECHNIQUES, look_id)
            self.assertIn(look["light"], C.LIGHTS, look_id)
            self.assertIn(look["grade"], C.GRADES, look_id)
            self.assertEqual(len({C.TECHNIQUES[t]["family"] for t in [look["technique"]] + look["also"]}), 4, look_id)
            self.assertGreaterEqual(len(look["makes"]), 3, look_id)
        blob = json.dumps(C.LOOKS)
        self.assertEqual(S.banned_names(blob), [])
        for name in S.LOOK_NAMES:
            self.assertIsNone(word(name).search(blob), name)

    def test_no_alias_reaches_any_output(self):
        """For every name: plan, choose and the files on disk hold the recipe and never the name."""
        for look_id, entry in S.LOOK_ALIASES.items():
            for alias in entry["names"]:
                name = alias.lstrip("~")
                out, text = self.plan(f"make it dramatic like {name}", name="n", subject="a chef", action="plating a dish",
                                      setting="a small kitchen")
                doc = json.loads((out / "options.json").read_text())
                self.assertEqual(doc["look"]["id"], look_id, name)
                self.assertEqual(doc["options"][0]["look_id"], look_id, name)
                self.assertEqual(S.validate_doc(doc), {}, name)
                code, chosen, _ = run(self.base("choose", "--options", str(out / "options.json"), "--pick", "A"))
                self.assertEqual(code, 0)
                if alias.startswith("~"):  # also a common word: it must be gone from the stored phrase
                    self.assertIsNone(word(name).search(doc["phrase"]), name)
                    continue
                for blob in (text, chosen, self.all_text(out)):
                    self.assertIsNone(word(name).search(blob), f"'{name}' leaked")

    def test_the_name_check_catches_a_leaked_alias(self):
        self.assertIn("the godfather", S.banned_names("a dinner like The Godfather"))
        self.assertTrue(S.lint_prompt("lit like Blade Runner 2049"))
        code, _, err = run(self.base("plan", "--phrase", "a push in", "--subject", "a man like Stanley Kubrick", "--out", str(self.dir / "x")))
        self.assertEqual(code, 2)
        self.assertIn("REFUSED", err)

    def test_the_named_look_is_option_a_and_says_what_makes_it(self):
        out, text = self.plan("dramatic like the Godfather dinner scene")
        doc = json.loads((out / "options.json").read_text())
        first = doc["options"][0]
        self.assertEqual((first["technique"], first["light"]["key"]), ("push_in", "top_pool"))
        self.assertIn("What makes that look", text)
        self.assertIn("The light comes from straight above", text)
        self.assertIn("LOOK:", first["image_prompt"])
        self.assertEqual(len({o["pro_term"] for o in doc["options"]}), 4)

    def test_genre_words_match_a_recipe(self):
        for phrase, look_id in {"a 90s music video": "music-video-gloss", "film noir detective": "noir-shadows",
                                "found footage": "found-footage", "like a skate video": "fisheye-skate-video"}.items():
            self.assertEqual(S.build_options(phrase)["look"]["id"], look_id, phrase)

    def test_common_words_are_not_names_without_a_cue(self):
        doc = S.build_options("two friends drive home in the rain")
        self.assertNotIn("look", doc)
        self.assertEqual(S.build_options("make it like Drive")["look"]["id"], "neon-night-city")

    def test_unknown_reference_is_never_guessed(self):
        out, text = self.plan("make it like Zorgon Wars Episode Nine")
        doc = json.loads((out / "options.json").read_text())
        self.assertTrue(doc["unknown_reference"])
        self.assertNotIn("look", doc)
        self.assertIn("UNKNOWN REFERENCE", text)
        self.assertNotIn("Zorgon", self.all_text(out) + text)

    def test_looks_command_lists_and_searches(self):
        code, out, _ = run(self.base("looks"))
        self.assertEqual(code, 0)
        self.assertIn(f"{len(C.LOOKS)} look recipe(s)", out)
        code, out, _ = run(self.base("looks", "--search", "the godfather"))
        self.assertIn("crime-drama-patriarch", out)
        self.assertNotIn("godfather", out.lower())
        code, out, _ = run(self.base("looks", "--search", "qwertyuiop"))
        self.assertIn("does not guess", out)

    def test_look_guide_is_name_free(self):
        text = "\n".join(p.read_text() for p in sorted((ROOT / "references" / "looks").glob("*.md")))
        for name in S.LOOK_NAMES:
            self.assertIsNone(word(name).search(text), name)


class FindingTheLook(Offline):
    def test_vagueness_is_deterministic(self):
        cases = {"make it feel epic but sad": True, "something nice and emotional": True, "qwertyuiop": True,
                 "the camera goes around them": False, "a slow push in, sad": False, "that swishy movement": False}
        for phrase, expected in cases.items():
            first = S.vagueness(phrase)
            self.assertEqual(first, S.vagueness(phrase))
            self.assertEqual(first[0], expected, phrase)
            self.assertEqual(bool(S.build_options(phrase).get("vague")), expected, phrase)
        _, text = self.plan("make it feel epic but sad")
        self.assertIn("LOOK NOT CLEAR", text)

    def test_refs_prints_search_links_only(self):
        code, out, _ = run(self.base("refs", "--query", "epic but sad mountain"))
        self.assertEqual(code, 0)
        links = re.findall(r"https?://\S+", out)
        self.assertEqual(len(links), len(C.REFERENCE_SITES) + 1)
        for link in links:
            self.assertTrue(link.startswith(S.SEARCH_URL), link)
            self.assertIn("epic+but+sad+mountain", link)
        self.assertIn("This tool opened nothing", out)
        self.assertIn("Never log in", out)
        self.assertFalse(any(self.dir.iterdir()))

    def start(self):
        out, _ = self.plan("make it feel epic but sad", subject="a lone hiker", action="reaching the top of a ridge",
                           setting="a mountain ridge in cloud")
        return out, str(out / "options.json")

    def test_round_changes_one_decision_only(self):
        out, options = self.start()
        code, text, _ = run(self.base("round", "--options", options, "--base", "A", "--vary", "light"))
        self.assertEqual(code, 0)
        doc = json.loads((out / "round_1" / "options.json").read_text())
        self.assertTrue(2 <= len(doc["options"]) <= 4)
        self.assertEqual(len({o["light"]["key"] for o in doc["options"]}), len(doc["options"]))
        for field in ("movement", "placement", "lens", "pro_term"):
            self.assertEqual(len({o[field] for o in doc["options"]}), 1, field)
        self.assertEqual(len({o["grade"]["key"] for o in doc["options"]}), 1)
        self.assertEqual(S.validate_doc(doc), {})
        code, card, _ = run(self.base("mock", "--options", str(out / "round_1" / "options.json"), "--backend", "openai", "--dry-run"))
        self.assertEqual(code, 0)
        self.assertIn("Round:     1 of 3", card)
        self.assertIn("Total:", card)

    def test_round_cap_is_enforced_and_can_be_raised(self):
        out, options = self.start()
        for vary in ("light", "height", "lens"):
            self.assertEqual(run(self.base("round", "--options", options, "--base", "A", "--vary", vary))[0], 0)
        code, _, err = run(self.base("round", "--options", options, "--base", "A", "--vary", "grade"))
        self.assertEqual(code, 2)
        self.assertIn("above the cap of 3 rounds", err)
        code, _, _ = run(self.base("round", "--options", options, "--base", "A", "--vary", "grade", "--max-rounds", "4"))
        self.assertEqual(code, 0)

    def test_a_rejected_value_is_not_shown_again(self):
        out, options = self.start()
        run(self.base("round", "--options", options, "--base", "A", "--vary", "light"))
        code, _, err = run(self.base("round", "--options", options, "--base", "A", "--vary", "light", "--reject", "light=moonlight",
                                     "--values", "moonlight,firelight"))
        self.assertEqual(code, 2)
        self.assertIn("rejected", err)
        code, _, _ = run(self.base("round", "--options", options, "--base", "A", "--vary", "light"))
        doc = json.loads((out / "round_2" / "options.json").read_text())
        self.assertNotIn("moonlight", [o["light"]["key"] for o in doc["options"]])

    def test_round_with_no_backend_says_the_look_is_less_certain(self):
        out, options = self.start()
        code, text, _ = run(self.base("round", "--options", options, "--base", "A", "--vary", "light"))
        self.assertIn("less certain", text)
        code, text, _ = run(self.base("mock", "--options", str(out / "round_1" / "options.json")))
        self.assertEqual(code, 0)
        self.assertIn("less certain", text)

    def test_lock_is_written_read_back_and_goes_stale_after_an_edit(self):
        out, options = self.start()
        code, text, _ = run(self.base("choose", "--options", options, "--pick", "A"))
        self.assertEqual(code, 0)  # choose works without a lock
        self.assertIn("UNLOCKED: decisions may still change", text)
        self.assertEqual(json.loads((out / "choice.json").read_text())["lock"]["status"], "UNLOCKED")
        code, _, err = run(self.base("lock", "--options", options, "--pick", "A", "--approval", "  "))
        self.assertEqual(code, 2)
        link = "https://example.org/some/still-page"
        args = ["lock", "--options", options, "--pick", "A", "--approval", "yes, that one", "--ref", link, "--at", "2026-11-15T12:00:00Z"]
        self.assertEqual(run(self.base(*args))[0], 0)
        first = (out / "look_lock.json").read_text()
        lock = json.loads(first)
        self.assertEqual(lock["approval"], "yes, that one")
        self.assertEqual(lock["references"][0]["url"], link)
        self.assertEqual(set(lock["locked"]), set(S.LOCK_PARTS))
        self.assertEqual(lock["locked_at"], "2026-11-15T12:00:00Z")
        run(self.base(*args))
        self.assertEqual((out / "look_lock.json").read_text(), first)  # deterministic
        run(self.base(*args[:-1], "2027-01-01T00:00:00Z"))
        later = json.loads((out / "look_lock.json").read_text())
        self.assertEqual({k: v for k, v in later.items() if k != "locked_at"}, {k: v for k, v in lock.items() if k != "locked_at"})
        code, text, _ = run(self.base("choose", "--options", options, "--pick", "A"))
        self.assertIn("LOCKED: the user approved", text)
        code, text, _ = run(self.base("choose", "--options", options, "--pick", "A", "--mix", "light=B"))
        self.assertEqual(code, 0)
        self.assertIn("LOCK IS STALE", text)
        # The link is provenance only: it is in the lock and in no other file.
        for path in out.rglob("*"):
            if path.is_file() and path.name != "look_lock.json":
                self.assertNotIn(link, path.read_text(encoding="utf-8", errors="replace"), path.name)

    def test_a_link_or_a_title_in_a_prompt_field_is_refused(self):
        code, _, err = run(self.base("plan", "--phrase", "a push in", "--setting", "like https://example.org/still", "--out", str(self.dir / "x")))
        self.assertEqual(code, 2)
        self.assertFalse((self.dir / "x").exists())

    def test_keep_writes_the_refined_options(self):
        out, options = self.start()
        run(self.base("round", "--options", options, "--base", "A", "--vary", "light"))
        code, text, _ = run(self.base("round", "--options", options, "--base", "A", "--keep", "light=overcast_soft", "--keep", "height=high"))
        self.assertEqual(code, 0)
        refined = json.loads((out / "refined.json").read_text())
        self.assertEqual(refined["options"][0]["light"]["key"], "overcast_soft")
        self.assertIn("3 m up", refined["options"][0]["placement"])
        self.assertEqual(run(self.base("lock", "--options", str(out / "refined.json"), "--pick", "A", "--approval", "lock it"))[0], 0)


class EnablerPaths(Offline):
    def test_fast_path_gives_a_prompt_without_an_options_round(self):
        code, out, _ = run(self.base("prompt", "--phrase", "slow push in on her face", "--subject", "a young woman",
                                     "--setting", "a train carriage at night"))
        self.assertEqual(code, 0)
        self.assertIn("SHOT: Push-in", out)
        self.assertIn("One line:", out)
        self.assertNotIn("Option B", out)
        self.assertFalse(any(self.dir.iterdir()))  # nothing is written unless --out is given
        code, out, _ = run(self.base("prompt", "--phrase", "whatever", "--technique", "whip_pan"))
        self.assertIn("SHOT: Whip pan", out)

    def test_detect_routing_text_matches_the_case(self):
        code, codex, _ = run(self.base("detect", "--image-tool", "image_gen"))
        self.assertIn("built-in image tool 'image_gen'", codex)
        self.assertIn("--backend host", codex)
        code, claude, _ = run(self.base("detect", "--no-image-tool"))
        self.assertIn("need an image model", claude)
        self.assertIn("HF_KEY", claude)
        self.assertIn("OPENAI_API_KEY", claude)
        self.assertIn("--import", claude)
        self.assertIn("Nothing is blocked", claude)
        self.assertNotIn("image_gen", claude)
        code, keyed, _ = run(self.base("detect", "--no-image-tool"), {"HF_KEY": HF_KEY, "OPENAI_API_KEY": "sk-test-THISISAFAKEKEY1234567890"})
        self.assertIn("openai: key found in process environment (selected)", keyed)
        self.assertIn("higgsfield: key found in process environment (available)", keyed)
        env = S.load_env(self.dir, environ={"REPLICATE_API_TOKEN": "r8_x", "FAL_KEY": "fal_x", "HF_KEY": HF_KEY, "OPENAI_API_KEY": "sk-test-x"})
        self.assertEqual([b["name"] for b in S.detect_backends(env)], ["openai", "higgsfield", "fal", "replicate"])
        self.assertLess(claude.index("OPENAI_API_KEY"), claude.index("HF_KEY"))
        self.assertNotIn(HF_KEY, keyed)
        self.assertNotIn("hfsecret", keyed)

    def test_mock_import_registers_user_images(self):
        out, _ = self.plan("the bullet time thingy")
        options = str(out / "options.json")
        source = self.dir / "from_my_tool.png"
        source.write_bytes(PNG)
        code, text, _ = run(self.base("mock", "--options", options, "--import", f"option_B={source}"))
        self.assertEqual(code, 0)
        self.assertEqual((out / "option_B.png").read_bytes(), PNG)
        self.assertIn("![Option B](option_B.png)", (out / "options.md").read_text())
        receipt = json.loads((out / "receipts.json").read_text())[0]
        self.assertEqual((receipt["status"], receipt["backend"]), ("imported", "user"))
        self.assertEqual(run(self.base("lock", "--options", options, "--pick", "B", "--approval", "that one"))[0], 0)
        self.assertEqual(json.loads((out / "look_lock.json").read_text())["mocks"][0]["path"], "option_B.png")
        bad = self.dir / "notes.txt"
        bad.write_text("not an image")
        self.assertEqual(run(self.base("mock", "--options", options, "--import", f"option_A={bad}"))[0], 2)
        self.assertEqual(run(self.base("mock", "--options", options, "--import", f"option_Z={source}"))[0], 2)

    def test_text_mode_prints_the_copy_paste_steps(self):
        code, out, _ = run(self.base("mock", "--phrase", "the bullet time thingy", "--out", str(self.dir / "o")))
        self.assertEqual(code, 0)
        self.assertIn("paste each prompt", out)
        self.assertIn("--import option_A=FILE", out)
        self.assertIn("option_A.png", out)

    def test_dry_run_gives_the_one_line_cost_question(self):
        code, out, _ = run(self.base("mock", "--phrase", "the bullet time thingy", "--backend", "openai", "--dry-run"))
        self.assertIn('"4 mock stills, about 0.28 USD - go?"', out)

    def test_higgsfield_request_shape_and_unknown_cost(self):
        calls = []

        def transport(method, url, headers, body=None, timeout=180):
            calls.append((method, url, headers, json.loads(body) if body else None))
            if method == "POST":
                return 200, json.dumps({"status": "queued", "request_id": "r1", "status_url": S.HIGGSFIELD_API + "/requests/r1/status"}).encode()
            if "/requests/" in url:
                return 200, json.dumps({"status": "completed", "images": [{"url": "https://cdn.example.org/a.png"}]}).encode()
            return 200, PNG

        image, extra = S.gen_higgsfield("a prompt", {"model": "some/endpoint"}, HF_KEY, "1536x864", "medium", {}, transport, sleep=lambda s: None)
        self.assertEqual(image, PNG)
        self.assertEqual(extra["request_id"], "r1")
        self.assertEqual([c[0] for c in calls], ["POST", "GET", "GET"])
        self.assertEqual(calls[0][1], S.HIGGSFIELD_API + "/some/endpoint")
        self.assertEqual(calls[0][2]["Authorization"], f"Key {HF_KEY}")
        self.assertEqual(calls[0][3], {"prompt": "a prompt"})
        self.assertNotIn("Authorization", calls[2][2])  # the key does not go to the file host
        # The price is unknown to the tool: a live run is refused until the user accepts.
        out = self.dir / "o"
        run(self.base("plan", "--phrase", "the bullet time thingy", "--out", str(out)))
        code, text, _ = run(self.base("mock", "--options", str(out / "options.json"), "--dry-run"), {"HF_KEY": HF_KEY})
        self.assertIn("Estimate:  unknown", text)
        fingerprint = re.search(r"--confirm (\w+)", text).group(1)
        code, _, err = run(self.base("mock", "--options", str(out / "options.json"), "--confirm", fingerprint), {"HF_KEY": HF_KEY})
        self.assertEqual(code, 2)
        self.assertIn("cost is unknown", err)
        self.assertNotIn("hfsecret", err)

    def test_failed_higgsfield_request_is_not_sent_again(self):
        posts = []

        def transport(method, url, headers, body=None, timeout=180):
            if method == "POST":
                posts.append(url)
                return 200, json.dumps({"status": "queued", "request_id": "r1", "status_url": S.HIGGSFIELD_API + "/requests/r1/status"}).encode()
            return 200, json.dumps({"status": "nsfw"}).encode()

        with self.assertRaises(S.ProviderError) as caught:
            S.gen_higgsfield("p", {"model": "m"}, HF_KEY, "", "", {}, transport, sleep=lambda s: None)
        self.assertFalse(caught.exception.ambiguous)
        self.assertEqual(len(posts), 1)


class SceneLight(Offline):
    def test_the_place_names_the_light_of_the_recommended_option(self):
        cases = {"a small dark kitchen with candles": "firelight", "a narrow brick alley at night": "practicals_night",
                 "a backyard lawn at sunset": "hard_backlight", "an empty car park on a grey day": "overcast_soft"}
        for setting, light in cases.items():
            doc = S.build_options("make it dramatic", setting=setting)
            self.assertIn(light, S.scene_lights({"setting": setting}), setting)
            self.assertIn(doc["options"][0]["light"]["key"], S.scene_lights({"setting": setting}), setting)
            self.assertEqual(S.validate_doc(doc), {})


class Sequences(Offline):
    def setUp(self):
        super().setUp()
        self.doc = S.build_options("two guys fight and I want to feel every punch", subject="two stunt fighters",
                                   action="one right hook lands", setting="a narrow alley at night")

    def test_cut_times_add_up_and_every_shot_is_long_enough(self):
        for pattern in C.SEQUENCES:
            for seconds in (10, 15, 30):
                seq = S.build_sequence(self.doc, "A", pattern, seconds)
                self.assertEqual(seq["shots"][0]["start_s"], 0.0)
                self.assertEqual(seq["shots"][-1]["end_s"], float(seconds))
                self.assertAlmostEqual(sum(s["seconds"] for s in seq["shots"]), seconds, places=5)
                self.assertTrue(all(s["seconds"] >= S.MIN_SHOT_SECONDS for s in seq["shots"]))
                self.assertEqual(sum(1 for s in seq["shots"] if s["hero"]), 1)
                self.assertEqual(S.lint_prompt(seq["prompt_block"]), [])
                self.assertEqual(seq, S.build_sequence(self.doc, "A", pattern, seconds))

    def test_prompt_states_the_rules(self):
        block = S.build_sequence(self.doc, "A", "impact", 10, anchor="the green door")["prompt_block"]
        for needle in ("5 shots joined by 4 hard cuts at exactly", "ONE ACTION AND ONE CAMERA MOVE IN EACH SHOT", "PEOPLE: exactly 2",
                       "within 2 m of the green door", "Nobody looks into the lens", "SPEED RULE", "LAST FRAME"):
            self.assertIn(needle, block)

    def test_a_contact_insert_hero_takes_the_contact_slot(self):
        label = next(o["label"] for o in self.doc["options"] if o["technique"] == "impact_insert")
        shots = S.build_sequence(self.doc, label, "impact", 10)["shots"]
        self.assertEqual([s["role"] for s in shots if s["hero"]], ["the contact"])

    def test_refusals(self):
        with self.assertRaises(S.Refusal):
            S.build_sequence(self.doc, "A", "impact", 3)
        with self.assertRaises(S.Refusal):
            S.build_sequence(self.doc, "A", "impact", 10, beats=["only one"])
        with self.assertRaises(S.Refusal):
            S.build_sequence(self.doc, "A", "impact", 10, anchor="the Nike sign")

    def test_cli_writes_the_files(self):
        out = self.dir / "s"
        S.write_outputs(self.doc, out)
        code, text, _ = run(self.base("sequence", "--options", str(out / "options.json"), "--pick", "A", "--pattern", "coverage"))
        self.assertEqual(code, 0)
        self.assertTrue((out / "sequence.json").exists() and (out / "sequence.md").exists())
        self.assertIn("[brackets]", text)


class Walkthrough(unittest.TestCase):
    def test_svg_is_xml_with_no_script_and_no_outside_link(self):
        text = (ROOT / "docs" / "replay.svg").read_text(encoding="utf-8")
        root = ET.fromstring(text)
        self.assertTrue(root.tag.endswith("svg"))
        tags = {node.tag.split("}")[-1] for node in root.iter()}
        self.assertNotIn("script", tags)
        self.assertNotIn("foreignObject", tags)
        self.assertNotRegex(text, r"\son[a-z]+=")
        self.assertIn("@keyframes", text)
        for node in root.iter():
            for key, value in node.attrib.items():
                if key.endswith("href"):
                    self.assertRegex(value, r"^data:image/(png|jpeg);base64,")
        self.assertNotIn("@import", text)
        self.assertNotIn("url(", text)

    def test_svg_and_data_hold_the_real_tool_output(self):
        data = json.loads((ROOT / "docs" / "walkthrough" / "data.json").read_text(encoding="utf-8"))
        example = ROOT / "examples" / data["example"]
        doc = json.loads((example / "options.json").read_text(encoding="utf-8"))
        self.assertEqual([o["pro_term"] for o in data["options"]], [o["pro_term"] for o in doc["options"]])
        self.assertEqual([o["video_snippet"] for o in data["options"]], [o["video_snippet"] for o in doc["options"]])
        choice = json.loads((example / "choice.json").read_text(encoding="utf-8"))
        key = "|".join([choice["picked"], choice["mixed"].get("light", choice["picked"]), choice["mixed"].get("grade", choice["picked"])])
        self.assertEqual(data["mixes"][key]["prompt_block"], choice["prompt_block"])
        transcript = "".join((example / "transcript" / f"{n}.txt").read_text(encoding="utf-8") for n in ("plan", "mock-dry-run", "choose"))
        for step in data["session"]:
            for line in step.get("lines", []):
                self.assertIn(line, transcript)
        for scene in data["scenes"]:
            tiers = json.loads((ROOT / "examples" / scene["slug"] / "tiers.json").read_text(encoding="utf-8"))
            self.assertEqual(scene["skill"]["prompt_block"], tiers["skill"]["prompt_block"])
        self.assertEqual((ROOT / "docs" / "walkthrough" / "data.js").read_text(encoding="utf-8").split("window.WALKTHROUGH = ", 1)[1].rstrip(";\n"),
                         (ROOT / "docs" / "walkthrough" / "data.json").read_text(encoding="utf-8").rstrip())

    def test_page_references_only_local_files(self):
        text = (ROOT / "docs" / "walkthrough" / "index.html").read_text(encoding="utf-8")
        self.assertNotRegex(text, r"https?://")
        self.assertNotRegex(text, r"(src|href)=[\"']//")
        self.assertEqual(re.findall(r"<script src=\"([^\"]+)\"", text), ["data.js"])
        self.assertNotIn("<link", text)
        self.assertNotIn("@import", text)
        self.assertNotIn("fetch(", text)
        data = json.loads((ROOT / "docs" / "walkthrough" / "data.json").read_text(encoding="utf-8"))
        paths = [o["image"] for o in data["options"]] + [s[t]["image"] for s in data["scenes"] if s["slug"] != "named-look" for t in ("bad", "plain", "skill")]
        for option in data["options"]:
            paths += list((option["previs"] or {}).get("files", {}).values())
        for path in paths:
            self.assertTrue((ROOT / path).is_file(), path)

    def test_readme_examples_match_the_committed_outputs(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for slug in ("dog-bullet-time", "skate-kickflip", "alley-fight", "birthday-candles", "named-look"):
            tiers = json.loads((ROOT / "examples" / slug / "tiers.json").read_text(encoding="utf-8"))
            choice = json.loads((ROOT / "examples" / slug / "choice.json").read_text(encoding="utf-8"))
            spec = (ROOT / "examples" / slug / "final_spec.md").read_text(encoding="utf-8")
            self.assertIn(choice["prompt_block"], spec, slug)
            self.assertEqual(choice["prompt_block"], tiers["skill"]["prompt_block"], slug)
            self.assertEqual(S.lint_prompt(choice["prompt_block"]), [], slug)
            # The README body shows the real video example. The mock-still scenes are 1 link each, with their files in examples/.
            self.assertNotIn(choice["prompt_block"], readme, slug)
            if slug != "named-look":
                self.assertIn(f"](examples/{slug}/)", readme, slug)
                self.assertNotIn(f"]({tiers['bad']['image']})", readme, slug)
                self.assertEqual(S.slop_tells(tiers["plain"]["prompt"]), [], slug)
                self.assertGreaterEqual(len(S.slop_tells(tiers["bad"]["prompt"], check_missing=True)), 5, slug)
            else:
                self.assertIn(f"](examples/{slug}/final_spec.md)", readme, slug)
        self.assertTrue(readme.lstrip().startswith("# shot-speak\n\n> **\"I want my dog to do a bullet time thingy"))
        lock = json.loads((ROOT / "examples" / "unclear-look" / "look_lock.json").read_text(encoding="utf-8"))
        self.assertIn(lock["approval"], readme)

    def test_readme_shows_the_real_video_example_from_its_files(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        base = ROOT / "examples" / "bike-cliff"
        tiers = json.loads((base / "tiers.json").read_text(encoding="utf-8"))
        options = json.loads((base / "options.json").read_text(encoding="utf-8"))
        sequence = json.loads((base / "sequence.json").read_text(encoding="utf-8"))
        self.assertIn(f"]({tiers['compare_gif']})", readme)
        self.assertIn(tiers["phrase"], readme)
        for row in tiers["tiers"]:
            prompt = (ROOT / row["prompt"]).read_text(encoding="utf-8").strip()
            self.assertIn(prompt, readme, row["key"])
            self.assertIn(row["what_you_get"], readme, row["key"])
            self.assertIn(f"({row['poster']})]({row['video']})", readme, row["key"])
            for path in (row["poster"], row["video"]):
                self.assertTrue((ROOT / path).is_file(), path)
            self.assertNotIn("@Image1", prompt, row["key"])
            self.assertEqual(S.lint_prompt(prompt), [], row["key"])
        by_key = {row["key"]: (ROOT / row["prompt"]).read_text(encoding="utf-8").strip() for row in tiers["tiers"]}
        self.assertGreaterEqual(len(S.slop_tells(by_key["noob"], check_missing=True)), 5)
        self.assertEqual(S.slop_tells(by_key["plain"]), [])
        self.assertEqual(S.slop_tells(by_key["skill"], check_missing=True), [])
        self.assertLess(len(by_key["skill"]), 2500)
        # The decisions and the shot list in the README are the ones in the committed plan and sequence.
        option = next(o for o in options["options"] if o["label"] == sequence["picked"])
        for value in (option["movement"], option["placement"], option["lens"], option["light"]["name"], option["grade"]["name"],
                      option["speed"]["name"]):
            self.assertIn(f"| {value} |", readme)
        for shot in sequence["shots"]:
            self.assertIn(f"| {shot['n']} | {shot['start_s']:g} to {shot['end_s']:g} s |", readme)
        self.assertIn("hard cuts at " + ", ".join(f"{c:g}" for c in sequence["cut_times_s"]) + " s", readme)
        # The 3_skill prompt is the sequence block with the 2 brackets filled.
        self.assertEqual(sequence["open_brackets"], 2)
        self.assertNotRegex(by_key["skill"], r"\[[^\]]+\]")

    def test_comparison_image_set_is_a_dry_run_by_default(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = build_images.main(["--dry-run", "--force", "--cwd", tempfile.gettempdir()], environ={})
        self.assertEqual(code, 0)
        text = out.getvalue()
        self.assertIn("Images:    16 to make", text)
        self.assertIn("Estimate:  1.12 USD", text)
        self.assertIn("NOT SENT", text)
        for name, prompt, _what in build_images.jobs():
            self.assertEqual(S.lint_prompt(prompt), [], name)


if __name__ == "__main__":
    unittest.main()
