"""Offline tests for the optional Blender blocking previs. One test runs Blender when a local Blender exists."""

import json
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import catalog as C  # noqa: E402
import previs as P  # noqa: E402
import shotspeak as S  # noqa: E402
from support import PHRASE, run  # noqa: E402

CTX = {"subject": "two masked ninjas", "action": "at the top of a jump off a low wall", "setting": "a walled courtyard at sunset",
       "aspect": "16:9"}


def doc():
    return S.build_options(PHRASE, CTX["subject"], CTX["action"], CTX["setting"])


class FakeDone:
    def __init__(self, stdout="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, "", returncode


def no_socket(address, timeout=None):
    raise ConnectionRefusedError()


class OpenSocket:
    closed = False

    def close(self):
        OpenSocket.closed = True


class Detection(unittest.TestCase):
    def detect(self, **hooks):
        base = {"which": lambda name: None, "exists": lambda path: False, "environ": {}, "platform": "linux",
                "run": lambda *a, **k: FakeDone("Blender 4.2.3 LTS\n"), "connect": no_socket}
        base.update(hooks)
        return P.detect(None, **base)

    def test_no_blender_gives_route_none_with_a_reason(self):
        found = self.detect()
        self.assertEqual(found["route"], "none")
        self.assertIsNone(found["blender"])
        self.assertIn("No Blender program was found", found["reason"])

    def test_blender_on_path_gives_route_headless(self):
        calls = []

        def fake_run(command, **kwargs):
            calls.append(command)
            return FakeDone("Blender 4.2.3 LTS\n\tbuild date: x\n")

        found = self.detect(which=lambda name: "/opt/b/blender", run=fake_run)
        self.assertEqual((found["route"], found["version"], found["blender"]), ("headless", "4.2.3", "/opt/b/blender"))
        self.assertEqual(calls, [["/opt/b/blender", "--version"]])  # the only command: no window opens

    def test_standard_folders_by_platform(self):
        mac = "/Applications/Blender.app/Contents/MacOS/Blender"
        self.assertEqual(self.detect(platform="darwin", exists=lambda p: p == mac)["blender"], mac)
        self.assertEqual(self.detect(platform="linux", exists=lambda p: p == "/snap/bin/blender")["blender"], "/snap/bin/blender")
        self.assertIn("/usr/bin/blender", P.candidate_paths({}, "linux"))
        self.assertEqual(P.candidate_paths({}, "win32"), [])

    def test_blender_variable_wins_and_a_bad_value_is_reported(self):
        found = P.detect("/custom/blender", exists=lambda p: p == "/custom/blender", which=lambda n: "/usr/bin/blender",
                         run=lambda *a, **k: FakeDone("Blender 5.2.2 LTS"), connect=no_socket)
        self.assertEqual((found["blender"], found["version"]), ("/custom/blender", "5.2.2"))
        bad = P.detect("/nowhere/blender", exists=lambda p: False, which=lambda n: None, connect=no_socket)
        self.assertEqual(bad["route"], "none")
        self.assertIn("BLENDER variable", bad["reason"])

    def test_open_mcp_socket_gives_route_mcp_and_sends_nothing(self):
        seen = []

        def connect(address, timeout=None):
            seen.append((address, timeout))
            return OpenSocket()

        found = P.detect(None, "localhost", 9911, which=lambda n: "/usr/bin/blender", exists=lambda p: False,
                         run=lambda *a, **k: FakeDone("Blender 4.5.0"), connect=connect)
        self.assertEqual(found["route"], "mcp")
        self.assertEqual(found["mcp"], {"host": "localhost", "port": 9911, "open": True})
        self.assertEqual(seen, [(("localhost", 9911), 0.5)])
        self.assertTrue(OpenSocket.closed)

    def test_mcp_without_a_program_is_still_mcp(self):
        self.assertEqual(self.detect(connect=lambda a, timeout=None: OpenSocket())["route"], "mcp")

    def test_a_program_that_reports_no_version_is_not_used(self):
        def broken(*args, **kwargs):
            raise OSError("cannot run")

        self.assertEqual(self.detect(which=lambda n: "/usr/bin/blender", run=broken)["route"], "none")

    def test_default_socket_is_local(self):
        self.assertEqual((P.MCP_DEFAULT_HOST, P.MCP_DEFAULT_PORT), ("localhost", 9876))


class Solver(unittest.TestCase):
    def test_same_options_give_byte_identical_scripts(self):
        first = [P.render_script(P.solve(o, CTX)) for o in doc()["options"]]
        second = [P.render_script(P.solve(o, CTX)) for o in json.loads(json.dumps(doc()))["options"]]
        self.assertEqual(first, second)
        self.assertEqual(len(set(first)), 4)
        for script in first:
            self.assertIn("PLAN = json.loads(", script)
            self.assertNotIn(P.PLAN_MARKER, script)
            compile(script, "blocking.py", "exec")  # valid Python
            self.assertNotIn("/Users/", script)

    def test_camera_follows_the_words_of_the_option(self):
        plans = {o["technique"]: P.solve(o, CTX) for o in doc()["options"]}
        arc = plans["frozen_arc"]["summary"]
        self.assertEqual((arc["start"]["lens_mm"], arc["start"]["distance_m"], arc["start"]["height_m"]), (35.0, 2.5, 1.6))
        self.assertAlmostEqual(arc["start"]["azimuth_deg"] - arc["end"]["azimuth_deg"], 130, delta=1)
        low = plans["low_wide_hero"]["summary"]
        self.assertEqual((low["start"]["lens_mm"], low["start"]["distance_m"], low["start"]["height_m"], low["camera_path_m"]),
                         (18.0, 3.0, 0.15, 0.0))

    def test_every_technique_solves_and_keeps_the_rules(self):
        ids = sorted(C.TECHNIQUES)
        self.assertEqual(set(ids), set(P.MOVES))
        for start in range(0, len(ids), 4):
            group = (ids[start:start + 4] + ids[:4])[:4]
            options = S.build_options("x", subject="two dancers", action="standing in the light", setting="an empty hall", techniques=group)
            for option in options["options"]:
                plan = P.solve(option, {k: options[k] for k in ("subject", "action", "setting", "aspect")})
                kind, samples = plan["kind"], plan["camera"]["samples"]
                self.assertEqual(len(samples), plan["frames"], option["technique"])
                self.assertEqual(len(plan["subjects"]), 2, option["technique"])
                self.assertTrue(all(len(s) == 8 and 8 <= s[6] <= 300 for s in samples), option["technique"])
                if kind not in ("overhead", "pov", "montage"):
                    self.assertTrue(all(s[1] <= 0.01 for s in samples), f"{option['technique']} crosses the action line")
                    self.assertFalse(any("faces the lens" in n for n in plan["notes"]), (option["technique"], plan["notes"]))
                self.assertEqual(plan["stills"], {"start": 1, "mid": (plan["frames"] + 1) // 2, "end": plan["frames"]})
                compile(P.render_script(plan), "blocking.py", "exec")

    def test_person_count_sides_and_facing(self):
        self.assertEqual([P.people_count(s) for s in ("a skateboarder", "two masked ninjas", "three friends", "4 dancers", "a crowd of 9 people")],
                         [1, 2, 3, 4, 4])
        fight = S.build_options("they fight", subject="two fighters", action="trading blows", setting="an alley")
        plan = P.solve(fight["options"][0], {k: fight[k] for k in ("subject", "action", "setting", "aspect")})
        left, right = plan["subjects"]
        self.assertLess(left["at"][0], right["at"][0])
        self.assertEqual((left["facing_deg"], right["facing_deg"]), (0.0, 180.0))  # they face each other, not the lens
        self.assertTrue(any(item["name"] == "wall_far" for item in plan["set"]))

    def test_frozen_moment_holds_the_people_and_moves_the_camera(self):
        arc = next(o for o in doc()["options"] if o["technique"] == "frozen_arc")
        plan = P.solve(arc, CTX)
        track = plan["subjects"][0]["track"]
        self.assertLess(abs(track[0][0] - track[-1][0]), 0.2)       # the people drift a hand's width
        self.assertGreater(track[len(track) // 2][2], 0.6)          # at the top of the jump
        self.assertGreater(plan["summary"]["camera_path_m"], 4.0)   # the camera travels

    def test_handheld_noise_is_seeded(self):
        fight = S.build_options("shaky like a documentary", subject="a chef", action="plating a dish", setting="a small kitchen")
        option = fight["options"][0]
        ctx = {k: fight[k] for k in ("subject", "action", "setting", "aspect")}
        a, b = P.solve(option, ctx), P.solve(option, ctx)
        self.assertEqual(a["camera"]["samples"], b["camera"]["samples"])
        self.assertNotEqual(a["camera"]["samples"][0][0:3], a["camera"]["samples"][10][0:3])
        other = dict(option, label="B")
        self.assertNotEqual(P.solve(other, ctx)["camera"]["samples"], a["camera"]["samples"])

    def test_hand_written_option_and_previs_override(self):
        option = {"label": "A", "pro_term": "My shot", "movement": "locked", "placement": "at knee height, side-on, 6 m away",
                  "lens": "135 mm", "duration": "2 s", "speed": {"key": "real_time"}}
        plan = P.solve(option, {"subject": "a runner", "action": "standing at the start line", "setting": "a field", "aspect": "9:16"})
        start = plan["summary"]["start"]
        self.assertEqual((start["height_m"], start["lens_mm"], round(start["azimuth_deg"])), (0.5, 135.0, 90))
        self.assertEqual(plan["resolution"], [360, 640])
        self.assertEqual(plan["frames"], 48)
        forced = P.solve(dict(option, previs={"kind": "arc", "az": [150, 40], "d": 3.0, "h": 1.2}),
                         {"subject": "a runner", "action": "standing", "setting": "a field", "aspect": "16:9"})
        self.assertEqual((forced["kind"], forced["summary"]["start"]["distance_m"]), ("arc", 3.0))

    def test_projection_matches_a_known_frame(self):
        sample = [0.0, -5.0, 1.0, 0.0, 0.0, 1.0, 36.0, 0.0]           # 5 m away, level, 36 mm on a 36 mm sensor
        centre = P.project([0.0, 0.0, 1.0], sample, (16, 9))
        self.assertEqual([round(v, 4) for v in centre], [0.0, 0.0, 5.0])
        right_edge = P.project([2.5, 0.0, 1.0], sample, (16, 9))      # half the width at 5 m is 2.5 m
        self.assertAlmostEqual(right_edge[0], 1.0, places=4)
        self.assertIsNone(P.project([0.0, -9.0, 1.0], sample, (16, 9)))  # behind the camera

    def test_an_animal_gets_a_small_stand_in(self):
        plan = P.solve(doc()["options"][0], dict(CTX, subject="a scruffy brown dog"))
        self.assertEqual((plan["subjects"][0]["shape"], plan["subjects"][0]["height"]), ("animal", P.ANIMAL_HEIGHT))
        self.assertTrue(any("four-legged" in n for n in plan["notes"]))

    def test_a_thrown_object_arrives_at_the_mouth_on_the_middle_frame(self):
        ctx = dict(CTX, subject="a scruffy brown dog", action="at the top of a jump, about to catch a thrown bone")
        low = next(o for o in doc()["options"] if o["technique"] == "low_wide_hero")
        plan = P.solve(low, ctx)
        prop, dog = plan["props"][0], plan["subjects"][0]
        mid = (plan["frames"] - 1) // 2
        self.assertEqual((prop["shape"], len(prop["track"])), ("bone", plan["frames"]))
        self.assertGreater(dog["track"][mid][2], 0.6)                                   # the dog is in the air at the peak
        mouth = [dog["track"][mid][0] + 0.56, dog["track"][mid][1], dog["track"][mid][2] + P.ANIMAL_HEAD_Z - 0.02]
        self.assertLess(max(abs(a - b) for a, b in zip(prop["track"][mid], mouth)), 0.02)
        self.assertGreater(prop["track"][0][0], prop["track"][mid][0] + 1.0)            # it comes from in front, off the frame
        self.assertAlmostEqual(prop["track"][-1][2] - dog["track"][-1][2], prop["track"][mid][2] - dog["track"][mid][2], places=3)  # it stays in the jaws
        for action, shape in {"catching a ball": "ball", "throws a frisbee": "disc", "fetching a stick": "stick"}.items():
            self.assertEqual(P.solve(low, dict(ctx, action=action))["props"][0]["shape"], shape)
        self.assertEqual(P.solve(low, dict(CTX, subject="a kid", action="catching a ball"))["props"][0]["track"][mid][2], 1.25)
        self.assertEqual(P.solve(low, CTX)["props"], [])                                 # no throw word, no prop
        compile(P.render_script(plan), "blocking.py", "exec")


class Command(unittest.TestCase):
    def setUp(self):
        self._connect = socket.create_connection
        socket.create_connection = no_socket
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        S.write_outputs(doc(), self.dir / "run")
        self.options = str(self.dir / "run" / "options.json")

    def tearDown(self):
        socket.create_connection = self._connect
        self.tmp.cleanup()

    def test_route_none_skips_says_why_and_exits_zero(self):
        code, out, _ = run(["--cwd", str(self.dir), "previs", "--options", self.options, "--blender", "/nowhere/blender"])
        self.assertEqual(code, 0)
        self.assertIn("PREVIS SKIPPED", out)
        self.assertIn("BLENDER variable does not point at a program", out)
        self.assertIn("The mock stills do not need Blender", out)
        manifest = json.loads((self.dir / "run" / "previs" / "previs.json").read_text())
        self.assertEqual(manifest["route"], "none")
        self.assertEqual([o["status"] for o in manifest["options"]], ["skipped"] * 4)
        self.assertTrue((self.dir / "run" / "previs" / "option_A" / "blocking.py").is_file())  # the scripts are kept for later
        # The mock stage still works after a skipped previs.
        self.assertEqual(run(["--cwd", str(self.dir), "mock", "--options", self.options, "--backend", "text"])[0], 0)
        self.assertEqual(run(["--cwd", str(self.dir), "choose", "--options", self.options, "--pick", "A"])[0], 0)
        self.assertNotIn("Blocking previs", (self.dir / "run" / "final_spec.md").read_text())

    def test_forced_headless_without_blender_is_refused(self):
        code, _, err = run(["--cwd", str(self.dir), "previs", "--options", self.options, "--route", "headless", "--blender", "/nowhere/blender"])
        self.assertEqual(code, 2)
        self.assertIn("needs a local Blender", err)

    def test_mcp_route_prints_code_and_never_starts_blender(self):
        calls = []
        real = subprocess.run
        subprocess.run = lambda *a, **k: calls.append(a) or FakeDone("")
        try:
            code, out, _ = run(["--cwd", str(self.dir), "previs", "--options", self.options, "--route", "mcp", "--only", "A,C",
                                "--blender", "/nowhere/blender"])
        finally:
            subprocess.run = real
        self.assertEqual(code, 0)
        self.assertEqual(calls, [])
        self.assertEqual(out.count("runpy.run_path("), 2)
        self.assertIn("--session", out)
        self.assertIn("--collect", out)
        self.assertIn("It does not change the user's scene", out)
        snippet = P.mcp_snippet(self.dir / "a.py", self.dir)
        compile(snippet, "snippet", "exec")

    def test_headless_command_line_and_failure_handling(self):
        command = P.headless_command("/b/blender", "/x/blocking.py", "/x", animatic=False)
        self.assertEqual(command[:4], ["/b/blender", "--background", "--factory-startup", "--python-exit-code"])
        self.assertEqual(command[-4:], ["--", "--out", "/x", "--no-animatic"])

        def slow(*args, **kwargs):
            raise subprocess.TimeoutExpired("blender", kwargs["timeout"])

        self.assertEqual(P.run_headless("/b", "s.py", "/x", timeout=7, run=slow), (False, "Blender did not finish in 7 s. It was stopped."))
        ok, message = P.run_headless("/b", "s.py", "/x", run=lambda *a, **k: FakeDone("Traceback\nValueError: boom", 1))
        self.assertFalse(ok)
        self.assertIn("ValueError: boom", message)

    def test_manifest_lists_files_with_hashes_and_relative_paths(self):
        previs_dir = self.dir / "run" / "previs"
        document = doc()
        plans = P.write_scripts(document, previs_dir, ["B"])
        folder = previs_dir / "option_B"
        for name in ("still_start.png", "still_mid.png", "still_end.png", "plan_overhead.png"):
            (folder / name).write_bytes(b"\x89PNG" + name.encode())
        (folder / "result.json").write_text(json.dumps({"engine": "BLENDER_WORKBENCH", "hidden": ["mid still: wall hides the head of S1."]}))
        manifest = P.collect(document, previs_dir, plans, "headless", {"version": "4.2.3"})
        self.assertEqual(json.loads((previs_dir / "previs.json").read_text()), manifest)
        entry = manifest["options"][0]
        self.assertEqual((entry["label"], entry["status"], entry["engine"]), ("B", "ok", "BLENDER_WORKBENCH"))
        self.assertEqual([f["role"] for f in entry["files"]], ["still_start", "still_mid", "still_end", "plan_overhead"])
        for item in entry["files"]:
            self.assertEqual(item["sha256"], P.sha256_file(previs_dir / item["path"]))
            self.assertFalse(item["path"].startswith("/"))
        self.assertEqual(entry["script_sha256"], P.sha256_file(folder / "blocking.py"))
        self.assertNotIn(str(self.dir), json.dumps(manifest))
        self.assertIn("never controls the look", manifest["use"])
        # choose picks the previs up, and --layout-ref adds 1 line to the prompt.
        code, out, _ = run(["--cwd", str(self.dir), "choose", "--options", self.options, "--pick", "B", "--layout-ref"])
        self.assertEqual(code, 0)
        self.assertIn("## Blocking previs", out)
        self.assertIn("LAYOUT REFERENCE:", out)
        self.assertIn("wall hides the head of S1", out)
        code, _, err = run(["--cwd", str(self.dir), "choose", "--options", self.options, "--pick", "A", "--layout-ref"])
        self.assertEqual(code, 2)

    def test_missing_stills_are_reported_as_not_rendered(self):
        previs_dir = self.dir / "run" / "previs"
        plans = P.write_scripts(doc(), previs_dir, ["A"])
        manifest = P.collect(doc(), previs_dir, plans, "mcp", {"version": None})
        self.assertEqual(manifest["options"][0]["status"], "not_rendered")


BLENDER = P.find_blender()[0]


@unittest.skipUnless(BLENDER and P.blender_version(BLENDER), "no local Blender")
class BlenderIntegration(unittest.TestCase):
    """Runs the real Blender without a window. Skipped on a machine with no Blender (for example in CI)."""

    def test_headless_run_writes_stills_plan_scene_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            S.write_outputs(doc(), Path(tmp) / "run")
            code, out, err = run(["--cwd", tmp, "previs", "--options", str(Path(tmp) / "run" / "options.json"), "--route", "headless",
                                  "--only", "A", "--size", "320", "--no-animatic"])
            self.assertEqual(code, 0, out + err)
            folder = Path(tmp) / "run" / "previs" / "option_A"
            for name in ("still_start.png", "still_mid.png", "still_end.png", "plan_overhead.png", "blocking.blend", "result.json"):
                self.assertTrue((folder / name).is_file(), name)
            png = (folder / "still_mid.png").read_bytes()
            self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(int.from_bytes(png[16:20], "big"), 320)
            self.assertEqual(int.from_bytes(png[20:24], "big"), 180)
            self.assertNotIn(tmp.encode(), png)
            manifest = json.loads((Path(tmp) / "run" / "previs" / "previs.json").read_text())
            self.assertEqual((manifest["route"], manifest["options"][0]["status"]), ("headless", "ok"))
            self.assertEqual({f["role"] for f in manifest["options"][0]["files"]}, {"still_start", "still_mid", "still_end", "plan_overhead", "blend"})
            # The 3 stills are different pictures: the camera moved.
            self.assertEqual(len({f["sha256"] for f in manifest["options"][0]["files"] if f["role"].startswith("still")}), 3)
            # The session mode builds a new scene and keeps what was there.
            session = subprocess.run([BLENDER, "--background", "--factory-startup", "--python-exit-code", "1", "--python-expr",
                                      "import bpy, runpy, sys\n"
                                      f"sys.argv = ['blender', '--', '--out', {str(folder / 'session')!r}, '--session', '--no-animatic']\n"
                                      f"runpy.run_path({str(folder / 'blocking.py')!r}, run_name='__main__')\n"
                                      "assert 'Cube' in bpy.data.objects and 'shotspeak_option_A' in bpy.data.scenes\n"],
                                     capture_output=True, text=True, timeout=240)
            self.assertEqual(session.returncode, 0, session.stdout[-600:] + session.stderr[-600:])
            self.assertTrue((folder / "session" / "still_mid.png").is_file())


if __name__ == "__main__":
    unittest.main()
