"""Offline regression tests for the request path: prompts that follow their decisions, the content-aware image cache,
the outgoing payload, and the checks on provider answers. Each test fails on 0.2.0. No test reaches the network."""

import base64
import json
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import shotspeak as S  # noqa: E402
from support import PHRASE, PNG, run  # noqa: E402

FAKE_KEY = "sk-test-THISISAFAKEKEY1234567890"
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\x11" * 40 + b"\xff\xd9"
WEBP = b"RIFF" + (4 + 22).to_bytes(4, "little") + b"WEBP" + b"VP8L" + (14).to_bytes(4, "little") + b"\x2f" + b"\x00" * 13


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

    def plan(self, **kw):
        out = self.dir / "plan"
        argv = ["plan", "--phrase", PHRASE, "--out", str(out)] + [x for k, v in kw.items() for x in (f"--{k}", v)]
        code, _, err = run(self.base(*argv))
        self.assertIn(code, (0, 3), err)
        return out / "options.json"

    def edit(self, path, label, **fields):
        doc = json.loads(path.read_text())
        option = next(o for o in doc["options"] if o["label"] == label)
        option.update(fields)
        path.write_text(json.dumps(doc))
        return doc


class PromptsFollowTheDecisions(Offline):
    """P0: an edited decision never leaves a stale prompt behind."""

    def test_edited_placement_reaches_the_mock_card_the_fingerprint_and_the_final_prompt(self):
        path = self.plan()
        _, before, _ = run(self.base("mock", "--options", str(path), "--backend", "openai", "--dry-run"))
        new = "on a balcony 6 m up, looking down at a steep angle, three-quarter to the subject"
        self.edit(path, "A", placement=new)
        _, after, _ = run(self.base("mock", "--options", str(path), "--backend", "openai", "--dry-run"))
        self.assertIn(f"Camera placement: {new}.", after)
        self.assertNotEqual(before.split("Card:")[1].split()[0], after.split("Card:")[1].split()[0])
        code, _, _ = run(self.base("choose", "--options", str(path), "--pick", "A"))
        self.assertEqual(code, 0)
        choice = json.loads((path.parent / "choice.json").read_text())
        self.assertIn(new, choice["one_line"])
        self.assertIn(new, choice["image_prompt"])
        self.assertIn(f"CAMERA PLACEMENT: {new}.", choice["prompt_block"])

    def test_every_decision_edit_rebuilds_both_prompts(self):
        doc = S.build_options(PHRASE)
        edits = {"lens": "135 mm", "movement": "a locked camera that does not move", "light": dict(doc["options"][0]["light"], prompt="one bare bulb above"),
                 "grade": dict(doc["options"][0]["grade"], prompt="black and white"), "speed": dict(doc["options"][0]["speed"], prompt="real time, crisp")}
        for field, value in edits.items():
            fresh = S.build_options(PHRASE)
            fresh["options"][0][field] = value
            S.validate_doc(fresh)
            option = fresh["options"][0]
            words = value["prompt"] if isinstance(value, dict) else value
            self.assertIn(words, option["video_snippet"], field)
            if field not in ("movement", "speed"):  # a still shows 1 frame: its moment comes from speed["still"]
                self.assertIn(words, option["image_prompt"], field)

    def test_subject_edit_after_planning_reaches_every_prompt(self):
        doc = S.build_options(PHRASE)
        doc["subject"] = "two masked dancers"
        S.validate_doc(doc)
        for option in doc["options"]:
            self.assertIn("two masked dancers", option["image_prompt"])
            self.assertIn("two masked dancers", option["video_snippet"].lower())

    def test_a_hand_edited_prompt_is_kept_while_its_decisions_stay(self):
        path = self.plan()
        own = "My own still: two ninjas at the top of a jump, seen side-on from the floor, 18 mm, one low hard sun."
        self.edit(path, "B", image_prompt=own)
        _, out, _ = run(self.base("mock", "--options", str(path), "--backend", "openai", "--dry-run"))
        self.assertIn(own, out)
        doc = json.loads(path.read_text())
        self.assertTrue(S.is_custom(doc["options"][1], "image_prompt"))

    def test_a_hand_edited_prompt_whose_decisions_changed_later_is_refused(self):
        path = self.plan()
        doc = self.edit(path, "B", image_prompt="My own still of the shot.")
        S.validate_doc(doc)  # the hand edit is accepted while nothing else changed
        doc["options"][1]["lens"] = "135 mm"
        with self.assertRaises(S.Refusal) as caught:
            S.validate_doc(doc)
        self.assertIn("edited by hand", str(caught.exception))

    def test_a_saved_prompt_from_an_old_version_that_does_not_match_is_rebuilt_and_said(self):
        doc = S.build_options(PHRASE)
        option = doc["options"][0]
        del option["prompt_basis"]  # an options.json from 0.2.0 has no record
        option["placement"] = "on a rooftop, 10 m up, looking straight down"
        notes = []
        S.validate_doc(doc, notes=notes)
        self.assertIn("on a rooftop, 10 m up", option["image_prompt"])
        self.assertTrue(any("rebuilt" in n for n in notes), notes)

    def test_a_height_round_states_the_new_height_and_drops_the_old_one(self):
        doc = S.build_options(PHRASE, techniques=["push_in", "low_wide_hero", "tracking_side"])
        round_doc = S.build_round(doc, "A", "height", 1)
        high = next(o for o in round_doc["options"] if o["value"] == "high")
        self.assertIn("3 m up, looking down", high["video_snippet"])
        self.assertNotIn("at eye height", high["video_snippet"])
        self.assertNotIn("eye height", high["image_prompt"].split("Camera placement:")[0])
        self.assertIn("chest-up", high["image_prompt"])  # the framing decision of the technique stays

    def test_mix_and_lock_follow_the_final_decisions(self):
        doc = S.build_options(PHRASE)
        choice = S.choose(doc, "A", ["lens=D"])
        self.assertIn(doc["options"][3]["lens"] + " lens", choice["one_line"])
        self.assertIn(f"LENS: {doc['options'][3]['lens']}", choice["image_prompt"])
        lock = S.build_lock(doc, choice, "yes", self.dir)
        doc["options"][0]["placement"] = "somewhere else entirely, 9 m away"
        S.validate_doc(doc)
        self.assertEqual(S.lock_status(S.choose(doc, "A", ["lens=D"]), lock), "STALE")


class ImageCache(Offline):
    """P0: an image is reused only for the exact request that made it."""

    def setUp(self):
        super().setUp()
        self.env = S.load_env(self.dir, environ={"OPENAI_API_KEY": FAKE_KEY})
        self.backend = S.select_backend(self.env)
        self.doc = S.build_options(PHRASE)
        self.out = self.dir / "o"
        self.calls = []

    def transport(self, method, url, headers, body=None, timeout=180):
        self.calls.append(json.loads(body)["prompt"][:40] if body else url)
        return 200, json.dumps({"data": [{"b64_json": base64.b64encode(PNG).decode()}]}).encode()

    def generate(self, doc=None, backend=None, size="1536x864", quality="medium", force=False):
        return S.generate(doc or self.doc, backend or self.backend, self.env, self.out, size, quality, self.transport,
                          force=force, log=lambda s: None)

    def test_the_same_request_twice_sends_nothing_the_second_time(self):
        self.generate()
        self.assertEqual(len(self.calls), 4)
        receipts = self.generate()
        self.assertEqual(len(self.calls), 4)
        self.assertEqual([r["status"] for r in receipts], ["reused"] * 4)

    def test_a_changed_prompt_requests_only_that_option(self):
        self.generate()
        self.doc["options"][2]["image_prompt"] += " One more decision."
        receipts = self.generate()
        self.assertEqual(len(self.calls), 5)
        self.assertEqual([r["status"] for r in receipts], ["reused", "reused", "ok", "reused"])

    def test_a_changed_model_size_or_quality_requests_every_image(self):
        self.generate()
        self.generate(backend=dict(self.backend, model="gpt-image-other"))
        self.assertEqual(len(self.calls), 8)
        self.generate(backend=dict(self.backend, model="gpt-image-other"), size="1024x1024")
        self.assertEqual(len(self.calls), 12)
        self.generate(backend=dict(self.backend, model="gpt-image-other"), size="1024x1024", quality="high")
        self.assertEqual(len(self.calls), 16)

    def test_a_corrupted_or_replaced_image_is_requested_again(self):
        self.generate()
        (self.out / "option_B.png").write_bytes(PNG[:-6])
        receipts = self.generate()
        self.assertEqual([r["status"] for r in receipts], ["reused", "ok", "reused", "reused"])

    def test_a_missing_receipt_is_never_a_cache_hit(self):
        self.generate()
        (self.out / "receipts.json").unlink()
        self.generate()
        self.assertEqual(len(self.calls), 8)

    def test_a_partial_run_keeps_its_receipts_and_the_next_run_finishes_it(self):
        def fail_on_c(method, url, headers, body=None, timeout=180):
            if json.loads(body)["prompt"] == self.doc["options"][2]["image_prompt"]:
                raise S.ProviderError("No answer from the provider: timed out", ambiguous=True)
            return self.transport(method, url, headers, body)

        S.generate(self.doc, self.backend, self.env, self.out, "1536x864", "medium", fail_on_c, log=lambda s: None)
        book = S.load_receipts(self.out)
        self.assertEqual({k: v["status"] for k, v in book.items()}, {"A": "ok", "B": "ok", "C": "ambiguous"})
        self.assertFalse(list(self.out.glob("option_C.*")))
        self.assertFalse(list(self.out.glob("*.part")))
        receipts = self.generate()
        self.assertEqual([r["status"] for r in receipts], ["reused", "reused", "ok", "ok"])

    def test_force_requests_every_image_again(self):
        self.generate()
        self.generate(force=True)
        self.assertEqual(len(self.calls), 8)

    def test_an_imported_image_is_kept_for_its_own_prompt_only(self):
        source = self.dir / "mine.jpg"
        source.write_bytes(JPEG)
        S.import_images(self.doc, self.out, [f"option_A={source}"], log=lambda s: None)
        receipts = self.generate()
        self.assertEqual(receipts[0]["status"], "imported")
        self.assertEqual(len(self.calls), 3)
        self.doc["options"][0]["image_prompt"] += " Changed."
        receipts = self.generate()
        self.assertEqual(receipts[0]["status"], "ok")
        self.assertEqual(sorted(p.name for p in self.out.glob("option_A.*")), ["option_A.png"])


class OutgoingRequest(Offline):
    """P0: configurable extra inputs never override the prompt or the image count, and the approval covers them."""

    def body(self, name, env, prompt="a prompt"):
        return S.request_for({"name": name, "model": "owner/model"}, prompt, "1536x864", "medium", env)[1]

    def test_extra_input_cannot_replace_the_prompt_or_multiply_the_images(self):
        for name, var in S.EXTRA_INPUT_VARS.items():
            for bad in ({"prompt": "something else"}, {"Prompt": "x"}, {"num_images": 4}, {"n": 2}, {"num_outputs": 3}):
                with self.assertRaises(S.Refusal, msg=(name, bad)):
                    self.body(name, {var: (json.dumps(bad), "test")})

    def test_extra_input_cannot_carry_a_link_a_path_or_a_name(self):
        for bad in ({"image_url": "https://example.org/me.jpg"}, {"ref": "/Users/someone/me.png"}, {"style": "like Pixar"},
                    {"nested": {"deep": ["mail@example.org"]}}, {"x": "data:image/png;base64,AAAA"}):
            with self.assertRaises(S.Refusal, msg=bad):
                self.body("fal", {"SHOTSPEAK_FAL_EXTRA_INPUT": (json.dumps(bad), "test")})

    def test_a_legitimate_extra_input_is_sent_and_bound_to_the_approval(self):
        env = {"SHOTSPEAK_FAL_EXTRA_INPUT": (json.dumps({"image_size": "landscape_16_9", "num_inference_steps": 28}), "test")}
        body = self.body("fal", env)
        self.assertEqual(body, {"image_size": "landscape_16_9", "num_inference_steps": 28, "prompt": "a prompt"})
        replicate = self.body("replicate", {"SHOTSPEAK_REPLICATE_EXTRA_INPUT": (json.dumps({"aspect_ratio": "16:9"}), "test")})
        self.assertEqual(replicate, {"input": {"aspect_ratio": "16:9", "prompt": "a prompt"}})
        backend = {"name": "fal", "model": "owner/model"}
        plain = S.request_fingerprint(backend, "1536x864", "medium", ["p"], {})
        with_extra = S.request_fingerprint(backend, "1536x864", "medium", ["p"], env)
        other = dict(env, SHOTSPEAK_FAL_EXTRA_INPUT=(json.dumps({"image_size": "square"}), "test"))
        self.assertEqual(len({plain, with_extra, S.request_fingerprint(backend, "1536x864", "medium", ["p"], other)}), 3)

    def test_a_changed_extra_input_after_the_yes_is_refused(self):
        out = self.dir / "o"
        run(self.base("plan", "--phrase", PHRASE, "--out", str(out)))
        env = {"FAL_KEY": "fal_secret_value_123456", "SHOTSPEAK_FAL_MODEL": "owner/model", "SHOTSPEAK_EST_USD_PER_IMAGE": "0.01",
               "SHOTSPEAK_FAL_EXTRA_INPUT": '{"image_size": "landscape_16_9"}'}
        _, text, _ = run(self.base("mock", "--options", str(out / "options.json"), "--dry-run"), env)
        fingerprint = text.split("--confirm ")[-1].split()[0]
        env["SHOTSPEAK_FAL_EXTRA_INPUT"] = '{"image_size": "square_hd"}'
        code, _, err = run(self.base("mock", "--options", str(out / "options.json"), "--confirm", fingerprint), env)
        self.assertEqual(code, 2)
        self.assertIn("does not match this card", err)
        self.assertNotIn("fal_secret_value_123456", err)

    def test_the_fingerprint_covers_the_request_and_the_shown_estimate(self):
        """The card shows the model, the image count and the estimate. The fingerprint is made of exactly those parts."""
        import hashlib
        backend = {"name": "openai", "model": S.OPENAI_DEFAULT_MODEL}
        payload = ["openai", S.OPENAI_DEFAULT_MODEL, "1536x864", "medium", ["a", "b"],
                   {"images": 2, "estimated_total_usd": round(2 * S.OPENAI_EST_USD_PER_IMAGE, 4)}]
        expected = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]
        self.assertEqual(S.request_fingerprint(backend, "1536x864", "medium", ["a", "b"], {}), expected)

    def test_a_model_id_cannot_change_the_endpoint_path(self):
        for model in ("../../v1/other", "owner//model", "owner/model?x=1", "https://evil.example/x", ""):
            with self.assertRaises(S.Refusal, msg=model):
                S.request_for({"name": "fal", "model": model}, "a prompt", "1536x864", "medium", {})


class ProviderAnswers(Offline):
    """P1: only 1 complete image is saved, under the extension of its real format."""

    def setUp(self):
        super().setUp()
        self.env = S.load_env(self.dir, environ={"OPENAI_API_KEY": FAKE_KEY})
        self.backend = S.select_backend(self.env)
        self.doc = S.build_options(PHRASE)
        self.out = self.dir / "o"

    def answer_with(self, data, out=None, force=False):
        def transport(method, url, headers, body=None, timeout=180):
            return 200, json.dumps({"data": [{"b64_json": base64.b64encode(data).decode()}]}).encode()
        return S.generate(self.doc, self.backend, self.env, out or self.out, "1536x864", "medium", transport, force=force,
                          log=lambda s: None)

    def test_png_jpeg_and_webp_get_their_own_extension_and_format(self):
        for data, suffix in ((PNG, ".png"), (JPEG, ".jpg"), (WEBP, ".webp")):
            receipts = self.answer_with(data, force=True)
            self.assertEqual(receipts[0]["file"], "option_A" + suffix)
            self.assertEqual(receipts[0]["format"], suffix[1:])
            self.assertEqual(sorted(p.suffix for p in self.out.glob("option_A.*")), [suffix])

    def test_a_bad_answer_is_ambiguous_saves_nothing_and_stops(self):
        for bad in (b"", b"<html>Bad gateway</html>", PNG[:-12], JPEG[:-2], b"RIFF\x00\x00\x00\x00WAVEfmt "):
            receipts = self.answer_with(bad, out=self.dir / "bad")
            self.assertEqual([r["status"] for r in receipts], ["ambiguous"], bad[:20])
            self.assertEqual([p.name for p in (self.dir / "bad").glob("option_*")], [])

    def test_invalid_base64_and_a_non_https_link_are_refused(self):
        def bad_b64(method, url, headers, body=None, timeout=180):
            return 200, json.dumps({"data": [{"b64_json": "not base64 !!"}]}).encode()

        def file_link(method, url, headers, body=None, timeout=180):
            if method == "GET":
                raise AssertionError("a non-https link was opened")
            return 200, json.dumps({"images": [{"url": "file:///etc/passwd"}]}).encode()

        with self.assertRaises(S.ProviderError):
            S.gen_openai("a prompt", self.backend, FAKE_KEY, "1536x864", "medium", {}, bad_b64)
        with self.assertRaises(S.ProviderError) as caught:
            S.gen_fal("a prompt", {"model": "owner/model"}, "fal_k", "1536x864", "medium", {}, file_link)
        self.assertTrue(caught.exception.ambiguous)

    def test_an_oversized_answer_is_refused_by_the_transport(self):
        class Big:
            status = 200

            def read(self, limit):
                return b"x" * limit

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        urllib.request.OpenerDirector.open = lambda *a, **k: Big()
        saved, S.MAX_ANSWER_BYTES = S.MAX_ANSWER_BYTES, 1000
        try:
            with self.assertRaises(S.ProviderError) as caught:
                S.http_transport("GET", "https://cdn.example.org/a.png", {})
        finally:
            S.MAX_ANSWER_BYTES = saved
        self.assertTrue(caught.exception.ambiguous)

    def test_a_cut_off_answer_is_an_ambiguous_provider_error(self):
        import http.client

        def cut(*a, **k):
            raise http.client.IncompleteRead(b"partial")

        urllib.request.OpenerDirector.open = cut
        with self.assertRaises(S.ProviderError) as caught:
            S.http_transport("GET", "https://cdn.example.org/a.png", {})
        self.assertTrue(caught.exception.ambiguous)


class Privacy(Offline):
    """P1: what can leave the machine, and what the text checks refuse. The checks are patterns, not a guarantee."""

    def test_the_whole_outgoing_body_is_the_prompt_and_fixed_fields(self):
        body = S.request_for({"name": "openai", "model": S.OPENAI_DEFAULT_MODEL}, "a prompt", "1536x864", "medium", {})[1]
        self.assertEqual(set(body), {"model", "prompt", "size", "quality", "n"})
        for name in ("fal", "higgsfield"):
            self.assertEqual(S.request_for({"name": name, "model": "owner/model"}, "a prompt", "", "", {})[1], {"prompt": "a prompt"})

    def test_private_data_patterns(self):
        for text in ("mail me at a.b@example.org", "see https://example.org/x", "file:///tmp/x.png", "~/Pictures/me.jpg",
                     "C:\\Pictures\\me.jpg", "sk-test-ABCDEFGHIJKLMNOPQRSTUV", "r8_test-ABCDEFGHIJKLMNOPQRSTUV", "data:image/png;base64,AAAA"):
            self.assertTrue(S.private_data(text), text)
        for text in ("a 135 mm lens, 3 m away", "a dark room at 10:30 pm", "metadata: none"):
            self.assertFalse(S.private_data(text), text)

    def test_a_prompt_with_private_data_is_refused_before_any_request(self):
        with self.assertRaises(S.Refusal):
            S.request_for({"name": "openai", "model": S.OPENAI_DEFAULT_MODEL}, "a still of /Users/someone/me.jpg", "1536x864", "medium", {})


if __name__ == "__main__":
    unittest.main()
