"""Offline tests for the visual medium and for the scope of a contradiction."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import catalog as C  # noqa: E402
import shotspeak as S  # noqa: E402
from support import PHRASE  # noqa: E402

LIVE_ONLY = ("live-action", "real gravity", "worn real textures", "photochemical", "fine grain", "visible grain", "real surface texture")


def all_prompts(doc):
    texts = [t for o in doc["options"] for t in (o["image_prompt"], o["video_snippet"])]
    for label in [o["label"] for o in doc["options"]]:
        choice = S.choose(doc, label)
        texts += [choice["prompt_block"], choice["one_line"], choice["image_prompt"]]
    texts.append(S.build_sequence(doc, "A", "build")["prompt_block"])
    return texts


class Medium(unittest.TestCase):
    def test_the_users_words_name_the_medium(self):
        for words, medium in (("stop-motion clay fox", "stop_motion"), ("a claymation snail", "stop_motion"),
                              ("a 3D animated robot", "3d_animation"), ("CGI dragon", "3d_animation"),
                              ("a watercolour illustration of a fox", "illustration"), ("a cartoon cat", "animation"),
                              ("hand-drawn 2D chase", "animation"), ("live action, handheld", "live_action"),
                              ("a dog jumps for a bone", "live_action"), ("an animated conversation at dinner", "live_action"),
                              ("a tennis match on a clay court", "live_action")):
            self.assertEqual(S.detect_medium(words), medium, words)

    def test_no_medium_leaves_the_output_as_before(self):
        doc = S.build_options(PHRASE)
        self.assertNotIn("medium", doc)
        self.assertNotIn("medium", json.dumps([o["prompt_basis"] for o in doc["options"]]))
        self.assertTrue(doc["options"][0]["image_prompt"].startswith("A single still frame from a live-action film"))

    def test_a_non_live_medium_gets_no_live_action_words(self):
        for medium, phrase, subject in (("stop_motion", "stop-motion, the fox tiptoes", "a clay fox puppet"),
                                        ("3d_animation", "a 3D animated robot jumps, make it epic", "a small robot"),
                                        ("illustration", "a watercolour illustration, slow push in", "a red fox"),
                                        ("animation", "cartoon chase, the camera follows behind", "a cartoon cat")):
            for techniques in (None, ["frozen_arc", "low_wide_hero", "macro_insert", "push_in"]):
                doc = S.build_options(phrase, subject, "at the top of a jump", "a quiet room", techniques=techniques)
                self.assertEqual(doc["medium"], medium)
                S.validate_doc(doc)
                for text in all_prompts(doc):
                    for words in LIVE_ONLY:
                        if medium == "stop_motion" and "grain" in words:
                            continue  # a stop-motion film is photographed: grain belongs to it
                        self.assertNotIn(words, text, (medium, words))
                self.assertIn(C.MEDIUMS[medium]["film"], doc["options"][0]["image_prompt"])

    def test_the_medium_is_said_in_1_line_and_can_be_set_in_options_json(self):
        doc = S.build_options("a 3D animated robot jumps over a crate")
        self.assertEqual(sum("medium" in n for n in doc["interpretation"]), 1)
        doc = S.build_options(PHRASE)
        doc["medium"] = "illustration"
        S.validate_doc(doc)
        self.assertIn("an illustrated film", doc["options"][0]["image_prompt"])
        doc["medium"] = "oil"
        with self.assertRaises(S.Refusal):
            S.validate_doc(doc)

    def test_the_decisions_stay_the_same_in_every_medium(self):
        live = S.build_options(PHRASE, "a fox")
        drawn = S.build_options(PHRASE + ", cartoon", "a fox")
        for a, b in zip(live["options"], drawn["options"]):
            for field in ("technique", "movement", "placement", "lens", "light", "speed"):
                self.assertEqual(a[field], b[field], field)


class ContradictionScope(unittest.TestCase):
    def contradicted(self, text):
        return {h["id"] for h in S.scan(text)[0] if h.get("contradiction")}

    def test_pairs_that_only_look_contradictory(self):
        for text in ("Real time; no slow motion except at the peak, where the jump plays in super slow motion. Side-on, 24 mm, low sun.",
                     "The camera never orbits; the dancer spins around twice. Low angle, 24 mm, one spotlight, real time.",
                     "SHOT 1: he falls in slow motion throughout, side-on, 85 mm, low sun.\nSHOT 2: real time, no slow motion, wide, 24 mm.",
                     "1. 0 to 2 s | he falls in slow motion throughout\n2. 2 to 4 s | real time, no slow motion",
                     "She looks straight into the camera; no lens flare. Side-on, 50 mm, window light, real time.",
                     "A man floats through the air; no slow floating camera drift. Side-on, 85 mm, window light, real time.",
                     "No slow motion outside shot 4.\nSHOT 4: the landing in slow motion throughout."):
            self.assertEqual(self.contradicted(text), set(), text)

    def test_real_contradictions(self):
        for text, tell in (("camera orbits around him in slow motion throughout; no orbiting camera", "orbit_full"),
                           ("SHOT 1: he falls in slow motion throughout, side-on, 85 mm.\nAVOID: slow motion.", "slowmo_everywhere"),
                           ("She looks into the camera and smiles. Nobody looks into the lens.", "eyes_to_lens"),
                           ("SHOT 1: a wet street at night, side-on, 35 mm; no glossy floor.\nSHOT 2: wide, 24 mm.", "glossy_floor"),
                           ("Volumetric fog fills the hall. No fog.", "bloom_haze")):
            self.assertIn(tell, self.contradicted(text), text)


if __name__ == "__main__":
    unittest.main()
