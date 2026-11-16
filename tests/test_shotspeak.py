"""Offline tests. No test may reach the network: setUp replaces urlopen with a bomb."""

import base64
import json
import os
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import catalog as C  # noqa: E402
import shotspeak as S  # noqa: E402
from support import PHRASE, PNG, run  # noqa: E402

FAKE_KEY = "sk-test-THISISAFAKEKEY1234567890"


class Offline(unittest.TestCase):
    def setUp(self):
        self._urlopen, self._open = urllib.request.urlopen, urllib.request.OpenerDirector.open

        def bomb(*args, **kwargs):
            raise AssertionError("A test tried to reach the network.")

        urllib.request.urlopen = bomb
        urllib.request.OpenerDirector.open = bomb
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        urllib.request.urlopen, urllib.request.OpenerDirector.open = self._urlopen, self._open
        self.tmp.cleanup()

    def base(self, *extra):
        return ["--cwd", str(self.dir), *extra]


class Detection(Offline):
    def test_no_key_selects_text_mode(self):
        self.assertEqual(S.select_backend(S.load_env(self.dir, environ={}))["name"], "text")

    def test_priority_openai_then_fal_then_replicate(self):
        env = S.load_env(self.dir, environ={"REPLICATE_API_TOKEN": "r8_x", "FAL_KEY": "fal_x", "OPENAI_API_KEY": FAKE_KEY})
        self.assertEqual([b["name"] for b in S.detect_backends(env)], ["openai", "fal", "replicate"])
        self.assertEqual(S.select_backend(env)["model"], S.OPENAI_DEFAULT_MODEL)
        self.assertEqual(S.select_backend(env, "fal")["name"], "fal")

    def test_env_local_is_read_and_process_environment_wins(self):
        (self.dir / ".env.local").write_text(f'OPENAI_API_KEY="{FAKE_KEY}"\nSHOTSPEAK_OPENAI_MODEL=custom-model\n')
        (self.dir / ".env").write_text("FAL_KEY=fal_from_env\n")
        env = S.load_env(self.dir, environ={})
        self.assertEqual(env["OPENAI_API_KEY"], (FAKE_KEY, ".env.local"))
        self.assertEqual(env["FAL_KEY"][1], ".env")
        self.assertEqual(S.select_backend(env)["model"], "custom-model")
        env = S.load_env(self.dir, environ={"OPENAI_API_KEY": "sk-from-process-0000000000"})
        self.assertEqual(env["OPENAI_API_KEY"][1], "process environment")

    def test_named_backend_without_key_is_refused(self):
        with self.assertRaises(S.Refusal):
            S.select_backend(S.load_env(self.dir, environ={}), "openai")

    def test_detect_never_prints_the_key(self):
        code, out, err = run(self.base("detect"), {"OPENAI_API_KEY": FAKE_KEY})
        self.assertEqual(code, 0)
        self.assertIn("openai: key found", out)
        self.assertNotIn(FAKE_KEY, out + err)

    def test_detect_without_key_names_the_next_step(self):
        code, out, _ = run(self.base("detect"))
        self.assertEqual(code, 0)
        self.assertIn("No image API key found", out)
        self.assertIn("--backend text", out)

    def test_fal_and_replicate_have_no_default_model(self):
        env = S.load_env(self.dir, environ={"FAL_KEY": "fal_x"})
        self.assertIsNone(S.select_backend(env)["model"])


class Planning(Offline):
    def test_bullet_time_phrase_gives_four_distinct_options(self):
        doc = S.build_options(PHRASE)
        self.assertEqual([o["technique"] for o in doc["options"]], ["frozen_arc", "fast_arc", "speed_ramp", "low_wide_hero"])
        self.assertEqual(len({o["pro_term"] for o in doc["options"]}), 4)
        self.assertEqual(len({C.TECHNIQUES[o["technique"]]["family"] for o in doc["options"]}), 4)
        self.assertEqual([o["recommended"] for o in doc["options"]], [True, False, False, False])
        self.assertTrue(doc["options"][0]["recommended_because"])
        self.assertIn("130 degrees", doc["options"][0]["movement"])

    def test_same_input_gives_same_output(self):
        self.assertEqual(json.dumps(S.build_options(PHRASE), sort_keys=True), json.dumps(S.build_options(PHRASE), sort_keys=True))

    def test_options_differ_in_light_and_grade(self):
        for phrase in (PHRASE, "make it look dramatic", "that swishy movement", "zoom in on them in slo-mo"):
            doc = S.build_options(phrase)
            self.assertGreaterEqual(len({o["light"]["key"] for o in doc["options"]}), 3, phrase)
            self.assertGreaterEqual(len({o["grade"]["key"] for o in doc["options"]}), 3, phrase)

    def test_amateur_phrases_map_to_the_expected_first_technique(self):
        expected = {"that swishy movement": "whip_pan", "make it look dramatic": "push_in",
                    "zoom in on them in slo-mo": "push_in", "the vertigo thing where the background stretches": "dolly_zoom",
                    "from above like a drone": "top_down", "follow her like a video game": "follow_behind",
                    "shaky like a documentary": "handheld_close", "fast cuts like a trailer": "fast_cut"}
        for phrase, first in expected.items():
            self.assertEqual(S.build_options(phrase)["options"][0]["technique"], first, phrase)

    def test_unknown_phrase_falls_back_and_says_so(self):
        doc = S.build_options("qwertyuiop")
        self.assertFalse(doc["matched"])
        self.assertEqual(len(doc["options"]), 4)
        self.assertIn("Ask the user", doc["interpretation"][0])

    def test_every_technique_builds_and_passes_all_checks(self):
        ids = sorted(C.TECHNIQUES)
        for start in range(0, len(ids), 4):
            group = (ids[start:start + 4] + ids[:4])[:4]
            doc = S.build_options("a test phrase", subject="a chef", action="plating a dish", setting="a small kitchen", techniques=group)
            self.assertEqual(S.validate_doc(doc), {}, group)

    def test_every_phrase_rule_points_at_real_techniques(self):
        for pattern, weight, ids, note, examples in C.PHRASE_RULES:
            self.assertEqual(len(ids), 4, pattern)
            first = examples.split(";")[0].strip()
            self.assertIn(ids[0], S.interpret(first)[0], first)
            for tech in ids:
                self.assertIn(tech, C.TECHNIQUES, pattern)
            self.assertEqual(len({C.TECHNIQUES[t]["family"] for t in ids}), 4, pattern)

    def test_plan_writes_options_files(self):
        out = self.dir / "run"
        code, text, _ = run(self.base("plan", "--phrase", PHRASE, "--subject", "two masked ninjas", "--out", str(out)))
        self.assertEqual(code, 0)
        self.assertTrue((out / "options.json").exists() and (out / "options.md").exists())
        md = (out / "options.md").read_text()
        for needle in ("Pro term to learn", "What the viewer feels", "Choose it when", "Risks with AI video generators",
                       "Say this to a video model", "AI look it avoids", "FRAME SKETCH", "TOP VIEW", "(recommended)"):
            self.assertIn(needle, md)
        self.assertIn("Anti-slop check: passed", text)


class PromptHygiene(Offline):
    def all_prompts(self):
        ids = sorted(C.TECHNIQUES)
        for start in range(0, len(ids), 4):
            group = (ids[start:start + 4] + ids[:4])[:4]
            doc = S.build_options("x", techniques=group)
            for option in doc["options"]:
                yield option["technique"], option["image_prompt"], option["video_snippet"]
            choice = S.choose(doc, "A", ["light=B", "grade=C"])
            yield "choice", choice["prompt_block"], choice["one_line"]

    def test_builder_never_emits_model_or_brand_names(self):
        for tech, image, video in self.all_prompts():
            self.assertEqual(S.banned_names(image), [], tech)
            self.assertEqual(S.banned_names(video), [], tech)

    def test_catalogue_text_has_no_model_or_brand_names(self):
        blob = json.dumps([C.TECHNIQUES, C.LIGHTS, C.GRADES, C.SPEEDS, C.LENSES])
        self.assertEqual(S.banned_names(blob), [])

    def test_brand_in_subject_is_refused(self):
        for subject in ("a hero like in the Matrix", "a Marvel superhero", "a runner in Nike shoes"):
            with self.assertRaises(S.Refusal, msg=subject):
                S.build_options(PHRASE, subject=subject)

    def test_private_data_in_subject_is_refused(self):
        for subject in ("my friend jo@example.org", "the person in /Users/someone/photo.png"):
            with self.assertRaises(S.Refusal, msg=subject):
                S.build_options(PHRASE, subject=subject)

    def test_mock_stills_keep_faces_off_the_lens(self):
        for tech, image, _ in self.all_prompts():
            if tech in ("choice", "pov"):
                continue
            self.assertIn("FACES: turned away from the lens", image, tech)
            self.assertIn("not a likeness of any real person", image, tech)

    def test_snippet_is_one_line(self):
        for _, _, video in self.all_prompts():
            self.assertNotIn("\n", video)


class AntiSlop(Offline):
    def test_builder_emits_avoid_clauses_for_the_relevant_tells(self):
        doc = S.build_options(PHRASE)
        frozen, low = doc["options"][0], doc["options"][3]

        def clause(tell):
            return C.SLOP_BY_ID[tell]["avoid"]

        for tell in ("orbit_full", "floating_bodies", "eyes_to_lens", "soft_glow", "bloom_haze", "glossy_floor",
                     "perfect_textures", "hdr_saturated", "flare_spam"):
            self.assertIn(clause(tell), frozen["image_prompt"], tell)
        for tell in ("orbit_full", "floating_bodies", "eyes_to_lens", "aquarium_speed", "bloom_haze"):
            self.assertIn(clause(tell), frozen["video_snippet"], tell)
        self.assertIn(clause("default_medium"), low["image_prompt"])
        self.assertIn("AVOID: ", frozen["image_prompt"])
        self.assertIn("Avoid: ", frozen["video_snippet"])

    def test_pinned_avoid_text(self):
        self.assertEqual(C.SLOP_BY_ID["eyes_to_lens"]["avoid"],
                         "nobody looks into the lens; every eyeline goes to a target inside the scene")
        self.assertEqual(C.SLOP_BY_ID["bloom_haze"]["avoid"], "no bloom, no haze, no fog, no volumetric god rays")
        self.assertEqual(C.SLOP_BY_ID["orbit_full"]["avoid"],
                         "the camera never completes a half circle and never reaches a view straight in front of the face")
        self.assertEqual(C.SLOP_BY_ID["aquarium_speed"]["avoid"],
                         "no slow floating camera drift; the camera is locked or makes one decisive move with a clear end")

    def test_real_time_snippets_forbid_slow_motion_drift(self):
        doc = S.build_options("that swishy movement")
        self.assertIn(C.SLOP_BY_ID["slowmo_everywhere"]["avoid"], doc["options"][0]["video_snippet"])

    def test_each_option_names_the_tells_it_avoids(self):
        for option in S.build_options(PHRASE)["options"]:
            self.assertTrue(1 <= len(option["slop_avoided"]) <= 2)

    def test_check_flags_a_sloppy_option(self):
        doc = S.build_options(PHRASE)
        bad = doc["options"][1]
        bad.update(movement="a slow floating camera orbit of 360 degrees around the subject", lens="50 mm",
                   placement="at chest height, in front of the subject", image_prompt="", video_snippet="")
        bad["light"] = {"key": "custom", "name": "glow", "prompt": "soft golden glow with volumetric fog on a wet street"}
        found = " ".join(S.validate_doc(doc)["B"])
        for needle in ("Aquarium speed", "Soft, even golden glow", "Bloom, haze", "Glossy wet floors",
                       "35 to 50 mm default", "An arc of 360 degrees"):
            self.assertIn(needle, found)

    def test_advice_never_blocks_a_confirmed_run(self):
        """Anti-slop findings are advice (owner rule: 4 hard gates only). The spend gate still needs the card's yes."""
        doc = S.build_options(PHRASE)
        doc["options"][1]["light"]["prompt"] = "soft golden glow, volumetric fog"
        path = self.dir / "options.json"
        path.write_text(json.dumps(doc))
        env = {"OPENAI_API_KEY": FAKE_KEY}
        code, out, _ = run(self.base("mock", "--options", str(path), "--dry-run"), env)
        self.assertEqual(code, 0)
        self.assertIn("Anti-slop advice", out)
        self.assertIn("Fine when:", out)
        code, _, err = run(self.base("mock", "--options", str(path), "--confirm", "anything"), env)
        self.assertEqual(code, 2)
        self.assertIn("does not match this card", err)
        fingerprint = out.split("--confirm ")[-1].split()[0]
        calls = []

        def transport(method, url, headers, body=None, timeout=180):
            calls.append(url)
            return 200, json.dumps({"data": [{"b64_json": base64.b64encode(PNG).decode()}]}).encode()

        saved, S.http_transport = S.http_transport, transport
        try:
            code, _, err = run(self.base("mock", "--options", str(path), "--confirm", fingerprint), env)
        finally:
            S.http_transport = saved
        self.assertEqual(code, 0, err)
        self.assertEqual(len(calls), 4)

    def test_negated_mentions_are_not_tells(self):
        self.assertEqual(S.slop_tells("No bloom, no haze, no fog. Nobody looks into the camera. Never a full orbit around them."), [])

    def test_deslop_flags_and_rewrites(self):
        text = ("Epic cinematic shot of a warrior standing in the center of the frame looking at the camera, "
                "slow floating camera orbits around him, golden glow, volumetric fog, wet street, 8k, teal and orange")
        tells, rewrite = S.deslop(text)
        ids = {t["id"] for t in tells}
        self.assertTrue({"frontal_centred", "eyes_to_lens", "orbit_full", "soft_glow", "bloom_haze", "glossy_floor",
                         "aquarium_speed", "hdr_saturated", "teal_orange_default", "vague_cinematic",
                         "missing_lens", "missing_camera", "missing_speed"} <= ids, ids)
        self.assertEqual({t["category"] for t in tells}, {"composition", "lighting", "lens", "motion", "finish"})
        self.assertEqual([t["id"] for t in S.slop_tells(rewrite)], [], rewrite)
        for gone in ("8k", "looking at the camera", "volumetric fog", "wet street", "Epic"):
            self.assertNotIn(gone, rewrite)
        self.assertIn("130 degrees", rewrite)
        self.assertIn("Lens: [", rewrite)

    def test_deslop_leaves_a_clean_prompt_alone(self):
        text = ("A chef plates a dish, seen side-on from a long lens at 85 mm, one hard window light from the left, "
                "real time, locked camera, the far side of the kitchen in shadow.")
        tells, rewrite = S.deslop(text)
        self.assertEqual(tells, [])
        self.assertEqual(rewrite, text)  # no boilerplate is added to a clean prompt

    def test_deslop_cli_flags_named_titles(self):
        code, out, _ = run(self.base("deslop", "--text", "A fight like John Wick, hdr"))
        self.assertEqual(code, 0)
        self.assertIn("john wick", out)
        self.assertIn("Over-saturated HDR look", out)

    def test_every_tell_has_why_and_fix_and_a_category(self):
        for tell in C.SLOP_TELLS:
            self.assertIn(tell["category"], ("composition", "lighting", "lens", "motion", "finish"))
            self.assertTrue(tell["why"] and tell["fix"] and tell["tell"])


class MockCard(Offline):
    def test_dry_run_prints_four_prompts_and_the_estimate_without_network(self):
        code, out, err = run(self.base("mock", "--phrase", PHRASE, "--backend", "openai", "--dry-run", "--out", str(self.dir / "o")))
        self.assertEqual(code, 0, err)
        self.assertEqual(out.count("A single still frame from a live-action film"), 4)
        self.assertIn("Estimate:  0.28 USD", out)
        self.assertIn("DRY RUN. Nothing was sent.", out)
        self.assertIn("OPENAI_API_KEY was not found", out)
        self.assertFalse((self.dir / "o").exists())

    def test_no_key_falls_back_to_text_mode_and_says_so(self):
        out_dir = self.dir / "o"
        code, out, _ = run(self.base("mock", "--phrase", PHRASE, "--out", str(out_dir)))
        self.assertEqual(code, 0)
        self.assertIn("No image backend", out)
        self.assertIn("Nothing was sent", out)
        md = (out_dir / "options.md").read_text()
        self.assertIn("TOP VIEW", md)
        self.assertIn("Mock image prompt", md)

    def test_host_mode_sends_nothing(self):
        code, out, _ = run(self.base("mock", "--phrase", PHRASE, "--backend", "host", "--out", str(self.dir / "o")),
                           {"OPENAI_API_KEY": FAKE_KEY})
        self.assertEqual(code, 0)
        self.assertIn("this tool sends nothing", out)
        self.assertNotIn(FAKE_KEY, out)

    def test_paid_run_without_confirmation_is_not_sent(self):
        code, out, _ = run(self.base("mock", "--phrase", PHRASE, "--out", str(self.dir / "o")), {"OPENAI_API_KEY": FAKE_KEY})
        self.assertEqual(code, 2)
        self.assertIn("NOT SENT", out)

    def test_wrong_fingerprint_is_refused(self):
        code, _, err = run(self.base("mock", "--phrase", PHRASE, "--confirm", "000000000000", "--out", str(self.dir / "o")),
                           {"OPENAI_API_KEY": FAKE_KEY})
        self.assertEqual(code, 2)
        self.assertIn("does not match this card", err)

    def test_fingerprint_changes_with_the_prompt(self):
        env = S.load_env(self.dir, environ={"OPENAI_API_KEY": FAKE_KEY})
        backend = S.select_backend(env)
        one = S.card(S.build_options(PHRASE), backend, "1536x864", "medium", env)
        two = S.card(S.build_options(PHRASE, subject="a skateboarder"), backend, "1536x864", "medium", env)
        self.assertNotEqual(one["fingerprint"], two["fingerprint"])

    def test_cap_refuses_too_many_images(self):
        code, _, err = run(self.base("mock", "--phrase", PHRASE, "--dry-run", "--max-images", "3"))
        self.assertEqual(code, 2)
        self.assertIn("above the cap of 3", err)
        code, _, err = run(self.base("mock", "--phrase", PHRASE, "--dry-run"), {"SHOTSPEAK_MAX_IMAGES": "2"})
        self.assertEqual(code, 2)
        code, _, _ = run(self.base("mock", "--phrase", PHRASE, "--dry-run", "--count", "3", "--max-images", "3"))
        self.assertEqual(code, 0)

    def test_dry_run_writes_no_file_in_any_mode(self):
        before = os.getcwd()
        os.chdir(self.dir)
        try:
            for backend in ("text", "host", "openai"):
                code, out, _ = run(self.base("mock", "--phrase", PHRASE, "--dry-run", "--backend", backend))
                self.assertEqual(code, 0)
                self.assertIn("DRY RUN", out)
            self.assertEqual(list(self.dir.iterdir()), [])
        finally:
            os.chdir(before)

    def test_usd_limit_refuses(self):
        env = {"OPENAI_API_KEY": FAKE_KEY}
        _, out, _ = run(self.base("mock", "--phrase", PHRASE, "--dry-run"), env)
        fingerprint = out.split("--confirm ")[-1].split()[0]
        code, _, err = run(self.base("mock", "--phrase", PHRASE, "--confirm", fingerprint, "--max-usd", "0.10"), env)
        self.assertEqual(code, 2)
        self.assertIn("above the limit", err)

    def test_unknown_cost_needs_explicit_acceptance(self):
        env = {"FAL_KEY": "fal_secret_value_123456", "SHOTSPEAK_FAL_MODEL": "some/model"}
        _, out, _ = run(self.base("mock", "--phrase", PHRASE, "--dry-run"), env)
        self.assertIn("Estimate:  unknown", out)
        fingerprint = out.split("--confirm ")[-1].split()[0]
        code, _, err = run(self.base("mock", "--phrase", PHRASE, "--confirm", fingerprint), env)
        self.assertEqual(code, 2)
        self.assertIn("The cost is unknown", err)

    def test_openai_size_rules(self):
        for bad in ("100x100", "1537x864", "4096x1024", "banana"):
            with self.assertRaises(S.Refusal, msg=bad):
                S.validate_size(bad)
        for size in S.ASPECTS.values():
            S.validate_size(size)


class Generation(Offline):
    """The live path with a fake transport. Nothing leaves the machine."""

    def setUp(self):
        super().setUp()
        self.env = S.load_env(self.dir, environ={"OPENAI_API_KEY": FAKE_KEY})
        self.backend = S.select_backend(self.env)
        self.doc = S.build_options(PHRASE)
        self.calls, self.logs = [], []

    def ok_transport(self, method, url, headers, body=None, timeout=180):
        self.calls.append((method, url, headers, body))
        answer = {"data": [{"b64_json": base64.b64encode(PNG).decode()}],
                  "usage": {"output_tokens": 1000, "input_tokens_details": {"text_tokens": 200, "image_tokens": 0}}}
        return 200, json.dumps(answer).encode()

    def test_one_request_per_option_and_files_written(self):
        out = self.dir / "o"
        receipts = S.generate(self.doc, self.backend, self.env, out, "1536x864", "medium", self.ok_transport, log=self.logs.append)
        self.assertEqual(len(self.calls), 4)
        self.assertEqual([r["status"] for r in receipts], ["ok"] * 4)
        for label in "ABCD":
            self.assertEqual((out / f"option_{label}.png").read_bytes(), PNG)
        body = json.loads(self.calls[0][3])
        self.assertEqual(body, {"model": S.OPENAI_DEFAULT_MODEL, "prompt": self.doc["options"][0]["image_prompt"],
                                "size": "1536x864", "quality": "medium", "n": 1})
        self.assertEqual(receipts[0]["measured_usd_at_published_rates"], 0.031)
        self.assertIn("![Option A](option_A.png)", (out / "options.md").read_text())

    def test_key_never_reaches_files_or_logs(self):
        out = self.dir / "o"
        S.generate(self.doc, self.backend, self.env, out, "1536x864", "medium", self.ok_transport, log=self.logs.append)
        written = "".join(p.read_text(errors="replace") for p in out.iterdir())
        self.assertNotIn(FAKE_KEY, written + "".join(self.logs))
        self.assertNotIn(FAKE_KEY, json.dumps(self.doc))

    def test_error_text_with_the_key_is_redacted(self):
        def leaky(method, url, headers, body=None, timeout=180):
            raise S.ProviderError(f"HTTP 401: Incorrect API key provided: {FAKE_KEY}", ambiguous=False)

        out = self.dir / "o"
        receipts = S.generate(self.doc, self.backend, self.env, out, "1536x864", "medium", leaky, log=self.logs.append)
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]["status"], "rejected")
        everything = "".join(self.logs) + (out / "receipts.json").read_text()
        self.assertNotIn(FAKE_KEY, everything)
        self.assertIn("[REDACTED]", everything)

    def test_ambiguous_failure_stops_and_is_never_retried(self):
        def timeout(method, url, headers, body=None, timeout=180):
            self.calls.append(url)
            raise S.ProviderError("No answer from the provider: timed out", ambiguous=True)

        receipts = S.generate(self.doc, self.backend, self.env, self.dir / "o", "1536x864", "medium", timeout, log=self.logs.append)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(receipts[0]["status"], "ambiguous")
        self.assertIn("NOT sent again", "".join(self.logs))

    def test_existing_image_without_a_receipt_is_requested_again(self):
        """A file name alone is not a cache key: an image with no receipt for this exact request is not reused."""
        out = self.dir / "o"
        out.mkdir()
        (out / "option_A.png").write_bytes(PNG)
        receipts = S.generate(self.doc, self.backend, self.env, out, "1536x864", "medium", self.ok_transport, log=self.logs.append)
        self.assertEqual(len(self.calls), 4)
        self.assertEqual(receipts[0]["status"], "ok")

    def test_second_and_third_backend_request_shapes(self):
        calls = []

        def transport(method, url, headers, body=None, timeout=180):
            calls.append((method, url, headers, body))
            if "fal.run" in url:
                return 200, json.dumps({"images": [{"url": "https://cdn.example/a.png"}]}).encode()
            if url.endswith("/predictions"):
                return 201, json.dumps({"id": "p1", "status": "processing", "urls": {"get": "https://" + "api.replicate.com/v1/predictions/p1"}}).encode()
            if url.endswith("/predictions/p1"):
                return 200, json.dumps({"id": "p1", "status": "succeeded", "output": ["https://cdn.example/b.png"]}).encode()
            return 200, PNG

        image, _ = S.gen_fal("a prompt", {"model": "owner/model"}, "fal_k", "1536x864", "medium", {}, transport)
        self.assertEqual(image, PNG)
        self.assertTrue(calls[0][1].endswith("/owner/model"))
        self.assertEqual(calls[0][2]["Authorization"], "Key fal_k")
        self.assertEqual(json.loads(calls[0][3]), {"prompt": "a prompt"})
        self.assertNotIn("Authorization", calls[1][2])
        calls.clear()
        image, extra = S.gen_replicate("a prompt", {"model": "owner/model"}, "r8_k", "1536x864", "medium", {}, transport,
                                       sleep=lambda s: None)
        self.assertEqual(image, PNG)
        self.assertEqual(extra["prediction_id"], "p1")
        self.assertTrue(calls[0][1].endswith("/v1/models/owner/model/predictions"))
        self.assertEqual(json.loads(calls[0][3]), {"input": {"prompt": "a prompt"}})

    def test_redact(self):
        self.assertEqual(S.redact(f"x {FAKE_KEY} y", [FAKE_KEY]), "x [REDACTED] y")
        self.assertIn("[REDACTED]", S.redact("Authorization: Bearer abcdefghijklmnop", []))


class Choosing(Offline):
    def setUp(self):
        super().setUp()
        self.out = self.dir / "o"
        run(self.base("plan", "--phrase", PHRASE, "--subject", "two masked ninjas", "--setting", "a walled courtyard at sunset", "--out", str(self.out)))

    def test_pick_writes_choice_and_final_spec(self):
        code, out, _ = run(self.base("choose", "--options", str(self.out / "options.json"), "--pick", "A"))
        self.assertEqual(code, 0)
        choice = json.loads((self.out / "choice.json").read_text())
        self.assertEqual(choice["picked"], "A")
        for head in ("SHOT:", "CAMERA MOVE:", "CAMERA PLACEMENT:", "LENS:", "LIGHT:", "COLOUR:", "SPEED:", "AVOID:"):
            self.assertIn(head, choice["prompt_block"])
        self.assertIn("two masked ninjas", choice["prompt_block"])
        self.assertEqual(choice["anti_slop_findings"], [])
        self.assertTrue((self.out / "final_spec.md").exists())

    def test_mix_takes_parts_from_other_options(self):
        doc = json.loads((self.out / "options.json").read_text())
        choice = S.choose(doc, "A", ["lens=D", "light=B"])
        self.assertEqual(choice["spec"]["lens"], doc["options"][3]["lens"])
        self.assertEqual(choice["spec"]["light"], doc["options"][1]["light"]["name"])
        self.assertEqual(choice["spec"]["movement"], doc["options"][0]["movement"])
        self.assertEqual(choice["mixed"], {"lens": "D", "light": "B"})

    def test_bad_pick_and_bad_mix_are_refused(self):
        doc = json.loads((self.out / "options.json").read_text())
        for pick, mix in (("Z", None), ("A", ["camera=B"]), ("A", ["lens=Z"]), ("A", ["lens"])):
            with self.assertRaises(S.Refusal):
                S.choose(doc, pick, mix)


class ValidateDoc(Offline):
    def test_variants_of_one_idea_are_refused(self):
        doc = S.build_options(PHRASE)
        doc["options"][1]["pro_term"] = doc["options"][0]["pro_term"]
        with self.assertRaises(S.Refusal):
            S.validate_doc(doc)

    def test_exactly_one_recommendation(self):
        doc = S.build_options(PHRASE)
        doc["options"][1]["recommended"] = True
        with self.assertRaises(S.Refusal):
            S.validate_doc(doc)

    def test_hand_written_option_with_a_brand_is_refused(self):
        doc = S.build_options(PHRASE)
        doc["options"][2]["image_prompt"] = "A still like a Pixar film."
        with self.assertRaises(S.Refusal):
            S.validate_doc(doc)


if __name__ == "__main__":
    unittest.main()
