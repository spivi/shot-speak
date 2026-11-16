"""Offline tests for the context-aware anti-slop check: negation scope, contradictions, techniques the user intends,
a proportional and idempotent rewrite, and prompts that never contradict the user's own words."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import catalog as C  # noqa: E402
import shotspeak as S  # noqa: E402
from support import run  # noqa: E402

CASES = json.loads((ROOT / "tests" / "fixtures" / "prompt_cases.json").read_text(encoding="utf-8"))["cases"]


def asked_part(rewrite):
    """The rewrite without the Avoid line that it can add at the end."""
    return rewrite.split(" Avoid: ")[0]


class EvaluationSet(unittest.TestCase):
    """The fixture is the offline evaluation set of docs/evaluation.md: exact tell ids, exact unchanged text."""

    def test_every_case(self):
        for case in CASES:
            with self.subTest(case["id"]):
                flagged, kept = S.scan(case["text"], check_missing=True)
                self.assertEqual(sorted(h["id"] for h in flagged), sorted(case["flagged"]))
                self.assertEqual(sorted(h["id"] for h in kept), sorted(case["kept"]))
                for tell_id in case.get("contradiction", []):
                    self.assertTrue(any(h["id"] == tell_id and h.get("contradiction") for h in flagged), tell_id)
                _tells, rewrite = S.deslop(case["text"])
                if case.get("unchanged"):
                    self.assertEqual(rewrite, case["text"])
                for words in case.get("keeps", []):
                    self.assertIn(words, rewrite)
                for words in case.get("drops", []):
                    self.assertNotIn(words, asked_part(rewrite))
                self.assertEqual(S.deslop(rewrite)[1], rewrite, "a second run changes nothing more")

    def test_the_set_covers_every_kind_of_case(self):
        ids = {c["id"] for c in CASES}
        self.assertGreaterEqual(len(CASES), 15)
        for needed in ("clean-film-literate", "user-negations-stay", "negation-scope", "contradiction", "fog-in-the-story",
                       "interview-eye-contact", "stop-motion", "product-turntable", "amateur-all-defaults"):
            self.assertIn(needed, ids)


class Rewrite(unittest.TestCase):
    def test_a_users_negations_are_never_rewritten(self):
        """0.2.0 turned 'No fog, no haze, no bloom' into 'No, no, no'."""
        text = "A man waits, side-on, 85 mm, one lamp, real time. No fog, no haze, no bloom, nobody looks into the camera."
        self.assertEqual(S.deslop(text + " Epic.")[1], text)

    def test_a_contradicted_slow_motion_is_not_brought_back(self):
        _tells, rewrite = S.deslop("a jump in slow motion throughout, side-on, 24 mm, low sun; no slow motion")
        self.assertNotIn("slow-motion beat", rewrite)
        self.assertIn("real time", rewrite)

    def test_the_guards_follow_the_findings(self):
        """No fixed boilerplate: the Avoid line holds only clauses for what was removed or left undecided."""
        _tells, rewrite = S.deslop("A boxer throws a jab, side-on, 85 mm, one hard top light, real time, 4k, lens flares")
        self.assertEqual(rewrite.split(" Avoid: ")[1],
                         C.SLOP_BY_ID["hdr_saturated"]["avoid"] + "; " + C.SLOP_BY_ID["flare_spam"]["avoid"] + ".")

    def test_the_cli_says_when_nothing_changes_and_shows_kept_choices(self):
        code, out, _ = run(["deslop", "--text", "Documentary interview: she looks into the camera, 50 mm, window light, real time, eye level."])
        self.assertEqual(code, 0)
        self.assertIn("[kept] Eyes into the lens", out)
        self.assertIn("Nothing to rewrite. The prompt is unchanged.", out)
        code, out, _ = run(["deslop", "--text", "volumetric fog everywhere, a man in a street", "--json"])
        data = json.loads(out)
        self.assertIn("fine_when", data["tells"][0])
        self.assertIn("kept", data)


class TellsAreAdvice(unittest.TestCase):
    def test_every_tell_says_when_it_is_fine_in_1_short_line(self):
        for tell in C.SLOP_TELLS:
            self.assertTrue(tell["fine_when"], tell["id"])
            self.assertLessEqual(len(tell["fine_when"].split()), 20, tell["id"])

    def test_the_slop_guide_states_each_fine_when_note(self):
        guide = (ROOT / "references" / "quality" / "slop-overview.md").read_text(encoding="utf-8")
        for tell in C.SLOP_TELLS:
            self.assertIn(tell["fine_when"], guide, tell["id"])

    def test_on_purpose_marks_any_tell_in_its_sentence(self):
        flagged, kept = S.scan("Teal and orange grade on purpose, side-on, 35 mm, low sun, real time.")
        self.assertEqual(flagged, [])
        self.assertEqual([h["id"] for h in kept], ["teal_orange_default"])

    def test_an_option_can_keep_a_tell_by_id(self):
        option = S.build_options("the bullet time thingy")["options"][0]
        option["movement"] = "a full 360 orbit around the subject"
        self.assertTrue(any("orbit" in f.lower() for f in S.anti_slop_check(option)))
        option["on_purpose"] = ["orbit_full"]
        self.assertFalse(any("orbit" in f.lower() for f in S.anti_slop_check(option)))


class PromptsRespectTheUsersWords(unittest.TestCase):
    """The builder never forbids what the user's own subject, action or place asks for."""

    def test_a_foggy_place_gets_no_no_fog_clause(self):
        doc = S.build_options("she walks out of the fog toward us", "a woman in a long coat", "walking out of the fog", "a foggy harbour at dawn")
        self.assertEqual(S.validate_doc(doc), {})
        for option in doc["options"]:
            for text in (option["image_prompt"], option["video_snippet"]):
                self.assertNotIn("no fog", text)
                self.assertIn(C.SLOP_BY_ID["bloom_haze"]["avoid_kept"], text)
        self.assertNotIn("no fog", S.choose(doc, "A")["prompt_block"])

    def test_an_action_into_the_lens_is_done_their_way_with_1_line_of_advice(self):
        doc = S.build_options("she turns to us", "a young woman", "turns and looks straight into the lens", "a crowded party")
        findings = S.validate_doc(doc)
        self.assertTrue(all(any("Eyes into the lens" in f and "Fine when:" in f for f in items) for items in findings.values()))
        for option in doc["options"]:
            self.assertNotIn("nobody looks into the lens", option["image_prompt"] + option["video_snippet"])
            self.assertNotIn("FACES: turned away from the lens", option["image_prompt"])
        sequence = S.build_sequence(doc, "A", "build")
        self.assertNotIn("Nobody looks into the lens", sequence["prompt_block"])

    def test_the_users_intent_removes_the_advice(self):
        doc = S.build_options("she breaks the fourth wall and looks straight into the camera", "a young woman",
                              "turns and looks straight into the lens", "a crowded party")
        self.assertEqual(S.validate_doc(doc), {})

    def test_rain_in_the_place_gets_no_dry_floor_clause(self):
        doc = S.build_options("the sneaker splashes into a puddle", "a running shoe", "landing in a puddle", "a city street in the rain")
        for option in doc["options"]:
            self.assertNotIn(C.SLOP_BY_ID["glossy_floor"]["avoid"], option["image_prompt"])

    def test_plain_words_keep_every_guard(self):
        """The fast path for an amateur phrase is not weakened: the usual clauses are all still there."""
        doc = S.build_options("make it look cool and epic, 4k, slow motion")
        image = doc["options"][0]["image_prompt"]
        for tell in C.STILL_BASE_AVOID:
            self.assertIn(C.SLOP_BY_ID[tell]["avoid"], image, tell)


if __name__ == "__main__":
    unittest.main()
