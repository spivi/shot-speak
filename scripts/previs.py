"""Blocking previs for shot-speak: the optional Blender stage.

This module has no Blender import. It does 4 things:

  detect   Find a local Blender, its version and a live Blender MCP socket.
  solve    Turn 1 option into a numeric blocking plan: where the people stand,
           where the camera is on every frame, the lens, the set boxes.
  script   Write the plan into a self-contained Blender Python script.
  run      Run that script with ``blender --background`` and hash the files.

The same options.json always gives the same plan and the same script, byte
for byte. Python 3 standard library only. Nothing here uses the network; the
MCP check is 1 TCP connection attempt to this machine.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

SCHEMA = 1
FPS = 24
SENSOR_MM = 36.0
PERSON_HEIGHT = 1.75
HEAD_Z = 1.62
DEFAULT_LONG_EDGE = 640
DEFAULT_TIMEOUT = 240
MCP_DEFAULT_HOST = "localhost"
MCP_DEFAULT_PORT = 9876
RUNTIME = Path(__file__).resolve().parent / "blender_blocking.py"
PLAN_MARKER = "PLAN = None  # shot-speak writes the blocking plan on this line\n"

ASPECT_RATIOS = {"16:9": (16, 9), "9:16": (9, 16), "1:1": (1, 1), "21:9": (21, 9), "4:3": (4, 3)}

# Identity colours for the chest band of each mannequin (RGB 0..1). The body stays grey.
SUBJECT_COLOURS = [("orange", [0.90, 0.45, 0.10]), ("blue", [0.15, 0.40, 0.85]),
                   ("green", [0.20, 0.65, 0.25]), ("purple", [0.55, 0.25, 0.75])]

# How each technique moves. Heights, distances and the lens come from the option's own words
# (``placement`` and ``lens``), so a hand-edited option still gives a matching previs.
# A value here fills only what the words do not state as a number.
MOVES = {
    "frozen_arc": {"kind": "arc", "az": (160, 30), "ease": "smooth"},
    "fast_arc": {"kind": "arc", "az": (178, 90), "ease": "out"},
    "whip_pan": {"kind": "whip"},
    "crash_zoom": {"kind": "zoom", "snap": True, "aim_h": 1.45},
    "push_in": {"kind": "dolly", "d_end": 1.8, "aim_h": 1.45},
    "dolly_zoom": {"kind": "dolly_zoom", "d": 2.0, "aim_h": 1.45},
    "slow_zoom": {"kind": "zoom", "snap": False, "aim_h": 1.3},
    "low_wide_hero": {"kind": "locked", "aim_h": 0.95, "az": 90},
    "long_lens_profile": {"kind": "locked", "push": 0.05, "aim_h": 1.45},
    "speed_ramp": {"kind": "track", "aim_h": 1.0},
    "tracking_side": {"kind": "track", "aim_h": 1.0, "foreground": "posts"},
    "follow_behind": {"kind": "follow"},
    "handheld_close": {"kind": "handheld", "aim_h": 1.4},
    "top_down": {"kind": "overhead"},
    "crane_reveal": {"kind": "crane", "d": 3.5, "az": 172, "foreground": "block"},
    "pull_back": {"kind": "dolly", "d_start": 1.6, "aim_h": 1.3},
    "locked_wide": {"kind": "locked", "aim_h": 1.0, "foreground": "edge"},
    "rack_focus": {"kind": "locked", "h": 1.0, "d": 4.6, "aim_h": 1.3, "foreground": "near"},
    "dutch_tilt": {"kind": "locked", "roll": 15, "aim_h": 1.1},
    "silhouette": {"kind": "locked", "d": 5.0, "aim_h": 1.0, "set": "opening"},
    "fast_cut": {"kind": "montage"},
    "pov": {"kind": "pov"},
    "macro_insert": {"kind": "locked", "h": 1.0, "d": 0.45, "aim_h": 1.0, "az": 90},
    "oner": {"kind": "oner"},
    "impact_insert": {"kind": "locked", "aim_h": 1.3, "jolt": True, "headroom": False},
}

HEIGHT_WORDS = {"floor": 0.15, "ground": 0.15, "knee": 0.5, "hip": 1.0, "waist": 1.0, "chest": 1.3,
                "shoulder": 1.45, "eye": 1.6, "head": 1.65}
_HEIGHT_RE = re.compile(r"on the (floor|ground)|(floor|ground|knee|hip|waist|chest|shoulder|eye|head)[- ]?(?:level|height)"
                        r"|(own) height|(\d+(?:\.\d+)?) m up", re.I)
_DIST_RE = re.compile(r"(\d+(?:\.\d+)?)(?: to (\d+(?:\.\d+)?))? m (?:away|back|or more|beyond)", re.I)
_PEOPLE_WORDS = {"one": 1, "a": 1, "an": 1, "two": 2, "both": 2, "pair": 2, "couple": 2, "three": 3, "trio": 3, "four": 4}
_OPPOSED_RE = re.compile(r"fight|duel|spar|punch|kick|strike|hit|attack|block|clash|wrestl|grappl|argu|confront|"
                         r"fac(e|es|ing) each other|face[- ]to[- ]face|stand[- ]?off|versus|against|opponent|rival", re.I)
_JUMP_RE = re.compile(r"jump|leap|flip|mid[- ]?air|in the air|airborne|vault|dive|hop", re.I)
_ANIMAL_RE = re.compile(r"\b(dog|puppy|cat|kitten|horse|pony|fox|wolf|deer|goat|sheep|cow|pig|rabbit|lion|tiger|bear|animal)s?\b", re.I)
ANIMAL_HEIGHT, ANIMAL_HEAD_Z = 0.72, 0.62
_THROW_RE = re.compile(r"throw|thrown|toss|catch|fetch|\b(bone|ball|frisbee|disc|stick)\b", re.I)
_PROP_SHAPES = [(r"\bbone\b", "bone"), (r"frisbee|\bdisc\b", "disc"), (r"\bstick\b", "stick"), (r"", "ball")]
THROW_SECONDS, THROW_FROM_M, THROW_FROM_Z = 0.9, 4.0, 1.3
_SPEED_WORDS = [(r"sprint|run|chas|dash|rac(e|ing)", 5.0), (r"skat|rid(e|ing)|cycl|bik", 6.0), (r"driv|car\b", 9.0),
                (r"walk|enter|arriv|stroll|approach|cross|march|step", 1.4)]


class PrevisError(Exception):
    """A previs that cannot be planned or run. The message is safe to print."""


def r4(value):
    value = round(float(value), 4)
    return 0.0 if value == 0 else value


def _lerp(a, b, u):
    return a + (b - a) * u


def _smooth(u):
    return u * u * (3 - 2 * u)


def _ease_out(u):
    return 1 - (1 - u) ** 3


def _polar(az_deg, dist, height):
    """Camera position for an azimuth. 0 = straight in front of the subject, 90 = side-on, 180 = behind.

    The subject faces +X. The camera side of the action line is -Y, so the subject moves to screen right.
    """
    a = math.radians(az_deg)
    return [dist * math.cos(a), -dist * math.sin(a), height]


def _add(a, b):
    return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]


def _sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _norm(a):
    length = math.sqrt(_dot(a, a)) or 1.0
    return [a[0] / length, a[1] / length, a[2] / length]


def camera_basis(pos, aim, roll_deg=0.0):
    """Right, up and forward unit vectors. The Blender script uses the same rule."""
    forward = _norm(_sub(aim, pos))
    right = _cross(forward, [0, 0, 1])
    if _dot(right, right) < 1e-8:
        right = [1.0, 0.0, 0.0]
    right = _norm(right)
    up = _cross(right, forward)
    if roll_deg:
        c, s = math.cos(math.radians(roll_deg)), math.sin(math.radians(roll_deg))
        right, up = ([right[i] * c + up[i] * s for i in range(3)], [up[i] * c - right[i] * s for i in range(3)])
    return right, up, forward


def project(point, sample, aspect):
    """Frame coordinates of a world point: x and y in -1..1 inside the frame, and the depth in m."""
    pos, aim, lens, roll = sample[0:3], sample[3:6], sample[6], sample[7]
    right, up, forward = camera_basis(pos, aim, roll)
    v = _sub(point, pos)
    depth = _dot(v, forward)
    if depth <= 1e-6:
        return None
    w, h = aspect
    half_w = SENSOR_MM / 2 if w >= h else SENSOR_MM / 2 * w / h
    half_h = half_w * h / w
    return [_dot(v, right) / depth * lens / half_w, _dot(v, up) / depth * lens / half_h, depth]


class Noise:
    """Seeded smooth noise: a sum of 3 sines. The same seed gives the same curve on every machine."""

    def __init__(self, seed):
        rng = random.Random(seed)
        self.waves = [[(rng.uniform(0.4, 1.0), rng.uniform(0.0, 6.2832), freq * rng.uniform(0.8, 1.2))
                       for freq in (0.7, 1.9, 4.3)] for _channel in range(6)]

    def at(self, channel, seconds):
        return sum(amp * math.sin(phase + 6.2832 * freq * seconds) for amp, phase, freq in self.waves[channel]) / 2.4


def seed_of(option):
    text = f"{option.get('label', '')}|{option.get('technique', '')}|{option.get('pro_term', '')}"
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)


# --------------------------------------------------------------------------
# Reading the option's words
# --------------------------------------------------------------------------
def parse_heights(placement, own=1.6):
    out = []
    for match in _HEIGHT_RE.finditer(placement or ""):
        ground, word, own_word, metres = match.groups()
        if metres:
            out.append(float(metres))
        elif own_word:
            out.append(own)
        else:
            out.append(HEIGHT_WORDS[(ground or word).lower()])
    return out


def parse_distances(placement):
    text = placement or ""
    out = [(float(a) + float(b)) / 2 if b else float(a) for a, b in _DIST_RE.findall(text)]
    if not out:
        if re.search(r"centimet", text, re.I):
            out.append(0.3)
        elif re.search(r"\bfar\b", text, re.I):
            out.append(9.0)
        elif re.search(r"\bclose\b", text, re.I):
            out.append(1.5)
    return out


def parse_azimuth(placement):
    text = (placement or "").lower()
    if re.search(r"three[- ]quarter (from )?behind|behind .*three[- ]quarter", text):
        return 145.0
    if "behind" in text:
        return 165.0
    if re.search(r"front three[- ]quarter", text):
        return 40.0
    if re.search(r"three[- ]quarter", text):
        return 50.0
    if re.search(r"side[- ]on|profile|parallel|from the side", text):
        return 90.0
    return 70.0


def parse_lens(lens):
    numbers = [float(n) for n in re.findall(r"(\d+(?:\.\d+)?) ?mm", lens or "")] or [float(n) for n in re.findall(r"\d+", lens or "")]
    return [min(300.0, max(8.0, n)) for n in numbers] or [35.0]


def parse_duration(text):
    numbers = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text or "")]
    seconds = sum(numbers[:2]) / len(numbers[:2]) if numbers else 4.0
    return min(12.0, max(1.0, seconds))


def people_count(subject):
    text = (subject or "").lower()
    match = re.search(r"\b(\d+)\b", text)
    if match:
        return max(1, min(4, int(match.group(1))))
    for word in re.findall(r"[a-z]+", text):
        if word in _PEOPLE_WORDS:
            return _PEOPLE_WORDS[word]
    return 2 if re.search(r"\b(people|performers|friends|kids|fighters|dancers|men|women)\b", text) else 1


def infer_kind(movement):
    text = (movement or "").lower()
    rules = [(r"arc|orbit|circl|around", "arc"), (r"whip", "whip"), (r"zoom.*travel|travel.*zoom", "dolly_zoom"),
             (r"zoom", "zoom"), (r"push|toward", "dolly"), (r"pull|travels away|back away", "dolly"),
             (r"track|lateral|parallel|alongside", "track"), (r"follow", "follow"), (r"handheld|hand-held", "handheld"),
             (r"rise|crane|lifts?|boom", "crane"), (r"straight down|overhead|top[- ]down", "overhead")]
    for pattern, kind in rules:
        if re.search(pattern, text):
            return kind
    return "locked"


# --------------------------------------------------------------------------
# Subjects
# --------------------------------------------------------------------------
def subject_layout(count, opposed):
    """Feet positions and facing for each person, with the group centre at the origin."""
    if opposed and count >= 2:
        spots = [([-0.55, 0.0], 0.0), ([0.55, 0.0], 180.0), ([1.9, 0.9], 180.0), ([2.1, -0.8], 180.0)][:count]
    else:
        spots = [([-(i * 1.2), 0.45 * i], 0.0) for i in range(count)]
    lead = spots[:2] if opposed else spots  # a fight stays centred on the first 2 people
    cx = sum(s[0][0] for s in lead) / len(lead)
    cy = sum(s[0][1] for s in lead) / len(lead)
    return [([r4(s[0][0] - cx), r4(s[0][1] - cy)], s[1]) for s in spots]


def world_rate(speed_key, u):
    """World time that passes for 1 s of screen time, at screen position u in 0..1."""
    if speed_key == "slow_motion":
        return 0.25
    if speed_key == "frozen_moment":
        return 0.03
    if speed_key == "speed_ramp":
        return 0.2 if 0.3 <= u <= 0.7 else 1.0
    if speed_key == "ramp_on_contact":
        return 0.25 if u < 0.5 else 1.0
    return 1.0


def world_times(speed_key, frames):
    """World time for every frame, with 0 at the middle frame: the peak of the action."""
    times, total = [0.0], 0.0
    for i in range(1, frames):
        total += world_rate(speed_key, (i - 0.5) / max(1, frames - 1)) / FPS
        times.append(total)
    mid = times[(frames - 1) // 2]
    return [t - mid for t in times]


def travel_speed(action, kind):
    for pattern, speed in _SPEED_WORDS:
        if re.search(pattern, action or "", re.I):
            return speed
    return 1.4 if kind in ("track", "follow", "oner") else 0.0


# --------------------------------------------------------------------------
# The solver
# --------------------------------------------------------------------------
def solve(option, ctx, long_edge=DEFAULT_LONG_EDGE):
    """Return the blocking plan for 1 option. Deterministic."""
    aspect = ASPECT_RATIOS.get(ctx.get("aspect", "16:9"), (16, 9))
    hint = dict(MOVES.get(option.get("technique"), {}))
    custom = option.get("previs") if isinstance(option.get("previs"), dict) else {}
    hint.update(custom)
    kind = hint.get("kind") or infer_kind(option.get("movement"))
    placement = option.get("placement", "")
    animal = bool(_ANIMAL_RE.search(ctx.get("subject", "")))
    head_z, body_h = (ANIMAL_HEAD_Z, ANIMAL_HEIGHT) if animal else (HEAD_Z, PERSON_HEIGHT)
    scale = head_z / HEAD_Z  # a camera that aims at a dog aims lower than a camera that aims at a person
    heights, dists = parse_heights(placement, 1.6 * scale + (0.5 if animal else 0.0)), parse_distances(placement)
    lenses = parse_lens(option.get("lens", ""))
    h = float(hint.get("h", heights[0] if heights else 1.4))
    d = float(hint.get("d", dists[0] if dists else 4.0))
    az = float(hint["az"]) if isinstance(hint.get("az"), (int, float)) else parse_azimuth(placement)
    level = "lens level" in placement.lower()
    aim_h = h if level and "aim_h" not in custom else float(hint.get("aim_h", 1.1 if d >= 3 else 1.4)) * (1.0 if "aim_h" in custom else scale)
    duration = float(hint.get("duration", parse_duration(option.get("duration"))))
    frames = max(12, int(round(duration * FPS)))
    speed_key = (option.get("speed") or {}).get("key", "real_time")
    action = ctx.get("action", "")
    seed = seed_of(option)
    noise = Noise(seed)
    notes = []

    # Subjects: where each person stands, which way each person faces, how the group travels.
    count = people_count(ctx.get("subject"))
    opposed = bool(_OPPOSED_RE.search(f"{ctx.get('subject', '')} {action}"))
    spots = subject_layout(count, opposed)
    speed = 0.0 if opposed else travel_speed(action, kind)
    jump = bool(_JUMP_RE.search(action)) and not opposed
    apex = 0.7
    half = math.sqrt(2 * apex / 9.81)
    times = world_times(speed_key, frames)
    forward = 1.5 if jump and not speed else speed
    centres = []
    for t in times:
        z = max(0.0, apex * (1 - (t / half) ** 2)) if jump else 0.0
        centres.append([forward * t, 0.0, z])
    moving = bool(forward or jump)
    subjects = []
    for index, (spot, facing) in enumerate(spots):
        name, colour = SUBJECT_COLOURS[index]
        item = {"id": f"S{index + 1}", "colour": name, "rgb": colour, "facing_deg": facing, "hidden": False,
                "shape": "animal" if animal else "person", "height": body_h, "head_z": head_z,
                "at": [spot[0], spot[1], 0.0]}
        if moving:
            item["track"] = [[r4(spot[0] + c[0]), r4(spot[1]), r4(c[2])] for c in centres]
        subjects.append(item)

    # A thrown object: it flies in from off the frame, in front of the first subject, and arrives at the
    # mouth (an animal) or the hands (a person) at the peak of the action. After that it stays there.
    props = []
    if _THROW_RE.search(action) and not opposed:
        shape = next(name for pattern, name in _PROP_SHAPES if re.search(pattern, action, re.I))
        reach = (0.56, head_z - 0.02) if animal else (0.38, 1.25)
        spot = spots[0][0]
        peak = centres[(frames - 1) // 2]
        target = [spot[0] + peak[0] + reach[0], spot[1], peak[2] + reach[1]]
        vz = (target[2] - THROW_FROM_Z + 0.5 * 9.81 * THROW_SECONDS ** 2) / THROW_SECONDS
        track = []
        for index, t in enumerate(times):
            if t >= 0:  # caught: it travels with the subject
                c = centres[index]
                at = [spot[0] + c[0] + reach[0], spot[1], c[2] + reach[1]]
            else:
                flown = t + THROW_SECONDS
                at = [target[0] + THROW_FROM_M * (-t / THROW_SECONDS), spot[1],
                      max(0.05, THROW_FROM_Z + vz * flown - 0.5 * 9.81 * flown ** 2)]
            track.append([r4(v) for v in at])
        props.append({"id": "P1", "shape": shape, "label": shape.upper(), "track": track})
        notes.append(f"The thrown object is a simple {shape} shape. It arrives at the middle frame. Its path is a real curve of gravity.")

    def centre(i, follow_jump=False):
        c = centres[i]
        return [c[0], 0.0, c[2] if follow_jump else 0.0]

    # Camera: 1 sample for each frame.
    samples, cuts, headroom = [], [], 0.0
    last = frames - 1
    for i in range(frames):
        u = i / last
        sec = i / FPS
        lens, roll = lenses[0], float(hint.get("roll", 0.0))
        if kind == "arc":
            a0, a1 = hint.get("az") if isinstance(hint.get("az"), (list, tuple)) else (az + 60, az - 60)
            degrees = re.findall(r"(\d{2,3}) degrees", option.get("movement", ""))
            if degrees and not isinstance(MOVES.get(option.get("technique"), {}).get("az"), tuple) and "az" not in custom:
                a1 = a0 - min(170, int(degrees[0]))
            ease = _ease_out if hint.get("ease") == "out" else _smooth
            pos = _polar(_lerp(a0, a1, ease(u)), d, h)
            aim = [0.0, 0.0, aim_h]
        elif kind == "whip":
            pos = _polar(az, d, h)
            sweep = min(1.0, max(0.0, (u - 0.3) / 0.2))
            aim = [_lerp(-1.8 * d, 0.0, sweep), 0.0, 1.3]
        elif kind == "zoom":
            pos = _polar(az, d, h)
            aim = [0.0, 0.0, aim_h]
            end = lenses[1] if len(lenses) > 1 else lenses[0] * 2
            if hint.get("snap", True):
                snap = min(1.0, max(0.0, (sec - 0.4 * duration) / 0.33))
                lens = _lerp(lenses[0], end, _smooth(snap))
                decay = max(0.0, 1 - (sec - 0.4 * duration - 0.33) / 0.6) if snap >= 1 else 0.0
                aim = [aim[0] + 0.05 * decay * noise.at(0, sec * 3), aim[1], aim[2] + 0.05 * decay * noise.at(1, sec * 3)]
            else:
                lens = _lerp(lenses[0], end, u)
        elif kind == "dolly":
            d0 = float(hint.get("d_start", d))
            d1 = float(hint.get("d_end", dists[-1] if len(dists) > 1 or "d_start" in hint and dists else max(1.2, d0 * 0.55)))
            pos = _polar(az, _lerp(d0, d1, _smooth(u)), h)
            aim = [0.0, 0.0, aim_h]
        elif kind == "dolly_zoom":
            end = lenses[1] if len(lenses) > 1 else lenses[0] * 2
            dist = _lerp(d, d * end / lenses[0], _smooth(u))
            lens = lenses[0] * dist / d
            pos = _polar(az, dist, h)
            aim = [0.0, 0.0, aim_h]
        elif kind == "track":
            c0 = centre(i)
            pos = _add(c0, _polar(90.0, d, h))
            aim = _add(c0, [0.0, 0.0, aim_h])
        elif kind == "follow":
            c0 = centre(i)
            bounce = 0.025 * math.sin(6.2832 * 1.9 * sec) + 0.012 * noise.at(2, sec)
            pos = _add(c0, [-d - 0.2, -0.38, h + bounce])
            aim = _add(c0, [2.5, 0.25, 1.35 + 0.02 * noise.at(3, sec)])
        elif kind == "handheld":
            base = _polar(az, d, h)
            pos = [base[0] + 0.035 * noise.at(0, sec), base[1] + 0.035 * noise.at(1, sec), base[2] + 0.03 * noise.at(2, sec)]
            lag = centres[max(0, i - 4)]
            aim = [lag[0] + 0.07 * noise.at(3, sec), 0.07 * noise.at(4, sec), aim_h + 0.05 * noise.at(5, sec)]
            roll = 1.5 * noise.at(4, sec * 0.7)
        elif kind == "overhead":
            pos = [0.0, 0.0, max(h, 3.0)]
            aim = [0.0, 0.0, 0.0]
        elif kind == "crane":
            h0, h1 = (heights + [4.0, 4.0])[:2]
            pos = _polar(az, d, _lerp(h0, h1, _smooth(u)))
            aim = [4.0, 0.0, 1.0]
        elif kind == "montage":
            shots = max(3, int(round(duration)))
            shot = min(shots - 1, int(u * shots))
            long_lens = lenses[1] if len(lenses) > 1 else 85.0
            setups = [(80, 3.0, 0.15, lenses[0], 0.95), (90, 7.0, 1.4, long_lens, 1.4), None, (60, 2.2, 1.2, long_lens, 1.2)]
            setup = setups[shot % 4]
            turn = 22.0 * (shot // 4)
            if not cuts or cuts[-1] != shot:
                cuts.append(shot)
            if setup is None:
                pos, aim, lens = [0.0, 0.0, 5.0], [0.0, 0.0, 0.0], lenses[0]
            else:
                pos, aim, lens = _polar(setup[0] + turn, setup[1], setup[2]), [0.0, 0.0, setup[4]], setup[3]
        elif kind == "pov":
            eye = subjects[0]["track"][i] if moving else subjects[0]["at"]
            step = 0.6 * u
            pos = [eye[0] + 0.12 + step, eye[1], eye[2] + 1.6 + 0.012 * noise.at(2, sec)]
            aim = [pos[0] + 3.0, pos[1] + 0.9 * math.sin(3.1416 * u) - 0.3, 1.35 - 0.5 * _smooth(max(0.0, (u - 0.6) / 0.4))]
        elif kind == "oner":
            c0 = centre(i)
            turn = _smooth(min(1.0, max(0.0, (u - 0.35) / 0.35)))
            pos = _add(c0, _polar(_lerp(90.0, 165.0, turn), _lerp(2.6, 1.6, turn), 1.45 + 0.015 * math.sin(6.2832 * 1.8 * sec)))
            aim = _add(c0, [0.6 * turn, 0.0, 1.35])
        else:  # locked
            push = float(hint.get("push", 0.0))
            pos = _polar(az, d - push * u, h)
            aim = [0.0, 0.0, aim_h]
            if hint.get("jolt") and opposed:  # frame the contact: the head of the person who takes the force
                aim = [0.33, 0.0, 1.52]
            if hint.get("jolt"):  # the frame kicks with the force at the contact, then settles
                kick = max(0.0, 1 - abs(sec - duration / 2 - 0.08) / 0.25) if sec >= duration / 2 else 0.0
                pos, aim = [pos[0] + 0.1 * kick, pos[1], pos[2]], [aim[0] + 0.1 * kick, aim[1], aim[2] + 0.03 * kick * noise.at(0, sec * 4)]
        samples.append(list(pos) + list(aim) + [lens, roll])

    # Headroom: an operator tilts up to keep heads in the frame. Raise the aim, by 0.8 m at most.
    if kind in ("arc", "zoom", "dolly", "dolly_zoom", "track", "handheld", "locked", "oner") and hint.get("headroom", True):
        mid = (frames - 1) // 2
        for _ in range(3):
            top = 0.0
            for index in (0, mid, last):
                for spot, _facing in spots:
                    c = centres[index]
                    seen = project([spot[0] + c[0], spot[1], c[2] + head_z + 0.12], samples[index], aspect)
                    if seen and abs(seen[0]) <= 1.2:
                        half_h = SENSOR_MM / 2 * (aspect[1] / aspect[0] if aspect[0] >= aspect[1] else 1.0)
                        top = max(top, (seen[1] - 0.88) * seen[2] * half_h / samples[index][6])
            lift = min(top, 0.8 - headroom)
            if lift <= 0.005:
                break
            headroom += lift
            for sample in samples:
                sample[5] += lift
    samples = [[r4(v) for v in sample] for sample in samples]

    if animal:
        notes.append("The stand-in is a simple four-legged shape. It shows the size and the position of the animal, not its body.")
    if kind == "pov":
        subjects[0]["hidden"] = True
        notes.append("Point of view: the camera is the first person. That person has no mannequin in the frame.")
    if option.get("technique") == "macro_insert":
        notes.append("A detail insert shows a grey shape in a previs. Use the mock still for this option.")
    if kind == "montage":
        notes.append(f"{len(cuts)} short shots with hard cuts. The 3 stills show 3 different camera positions.")

    cam_points = [s[0:3] for s in samples]
    reach = max([abs(v) for p in cam_points for v in p[0:2]] + [abs(v) for c in centres for v in c[0:2]] + [6.0])
    stills = {"start": 1, "mid": (frames + 1) // 2, "end": frames}
    plan = {
        "schema": SCHEMA, "label": option.get("label", "?"), "technique": option.get("technique", "custom"),
        "pro_term": option.get("pro_term", ""), "aspect": ctx.get("aspect", "16:9"), "fps": FPS, "frames": frames,
        "duration_s": r4(frames / FPS), "resolution": resolution(aspect, long_edge), "seed": seed, "kind": kind,
        "speed": speed_key, "camera": {"sensor_mm": SENSOR_MM, "samples": samples},
        "subjects": subjects, "props": props, "stills": stills, "floor_half": int(min(40, math.ceil(reach + 6))),
        "set": build_set(ctx, hint, samples, centres, d),
    }
    plan["summary"] = summarise(plan, option, centres)
    plan["checks"] = framing_checks(plan, aspect)
    plan["notes"] = notes + check_notes(plan)
    return plan


def resolution(aspect, long_edge):
    w, h = aspect
    if w >= h:
        return [int(long_edge), int(round(long_edge * h / w / 2) * 2)]
    return [int(round(long_edge * w / h / 2) * 2), int(long_edge)]


def build_set(ctx, hint, samples, centres, d):
    """Grey boxes for the place. The camera side of the action line stays open."""
    text = f"{ctx.get('setting', '')} {ctx.get('action', '')}".lower()
    setting = (ctx.get("setting") or "").lower()
    cam_y = min(s[1] for s in samples)
    cam_x0, cam_x1 = min(s[0] for s in samples), max(s[0] for s in samples)
    x0 = min(cam_x0, min(c[0] for c in centres)) - 3
    x1 = max(cam_x1, max(c[0] for c in centres)) + 3
    items = []

    def box(name, at, size, shade="wall"):
        items.append({"type": "box", "name": name, "at": [r4(v) for v in at], "size": [r4(v) for v in size], "shade": shade})

    def post(name, at, radius, height, shade="prop"):
        items.append({"type": "post", "name": name, "at": [r4(v) for v in at], "radius": r4(radius), "height": r4(height), "shade": shade})

    span, mid = x1 - x0, (x0 + x1) / 2
    if hint.get("set") == "opening" or re.search(r"door|gate|arch|window|opening", setting):
        back, wide, tall = 3.0, max(span, 10.0), 3.0
        side = (wide - 1.8) / 2
        box("opening_left", [-0.9 - side / 2, back, 0], [side, 0.3, tall])
        box("opening_right", [0.9 + side / 2, back, 0], [side, 0.3, tall])
        box("opening_top", [0, back, 2.3], [1.8, 0.3, tall - 2.3])
    elif re.search(r"alley|corridor|hallway|tunnel|aisle|passage", setting):
        box("wall_far", [mid, 1.7, 0], [span + 50, 0.3, 3.2])
        box("wall_near", [mid, cam_y - 0.9, 0], [span + 50, 0.3, 3.2])
    elif re.search(r"courtyard|walled|yard|arena|ring", setting):
        far = max(8.0, -cam_y + 2.5)
        box("wall_back", [mid, 7.0, 0], [span + 12, 0.4, 3.0])
        box("wall_left", [x0 - 6, (7.0 - far) / 2, 0], [0.4, 7.0 + far, 3.0])
        box("wall_right", [x1 + 6, (7.0 - far) / 2, 0], [0.4, 7.0 + far, 3.0])
        box("wall_front", [mid, -far, 0], [span + 12, 0.4, 3.0])
    elif re.search(r"room|office|kitchen|garage|studio|gym|bar\b|shop|warehouse|hall\b|club|interior|inside|indoor", setting):
        box("wall_back", [mid, 4.0, 0], [span + 6, 0.3, 3.0])
        box("wall_left", [x0 - 3, (4.0 + cam_y) / 2 - 1, 0], [0.3, 6.0 - cam_y, 3.0])
        box("wall_right", [x1 + 3, (4.0 + cam_y) / 2 - 1, 0], [0.3, 6.0 - cam_y, 3.0])
    if re.search(r"low wall|ledge|kerb|curb|step\b", text):
        box("low_wall", [min(c[0] for c in centres) - 1.6, 0.3, 0], [0.45, 3.6, 0.6], "prop")
    if re.search(r"table|desk|counter|bench|crate", text):
        box("table", [1.4, 1.5, 0], [1.6, 0.8, 0.75], "prop")
    if re.search(r"tree|pillar|column|lamp|pole", text):
        for n, x in enumerate((-3.5, 0.5, 4.5)):
            post(f"pillar_{n + 1}", [x, 3.0, 0], 0.22, 3.2)
    foreground = hint.get("foreground")
    first = samples[0]
    right, _up, forward = camera_basis(first[0:3], first[3:6])
    if foreground == "posts":
        x = math.floor(x0)
        n = 0
        while x <= x1:
            n += 1
            post(f"fg_post_{n}", [x, -d * 0.45, 0], 0.07, 2.6)
            x += 2.5
    elif foreground == "block":
        box("fg_block", [first[0] + forward[0] * 0.9, first[1] + forward[1] * 0.9, 0], [0.5, 1.6, 0.75], "prop")
    elif foreground == "edge":
        at = [first[0] + forward[0] * 1.6 - right[0] * 0.95, first[1] + forward[1] * 1.6 - right[1] * 0.95, 0]
        box("fg_edge", at, [0.5, 0.5, 2.6], "dark")
    elif foreground == "near":
        at = [first[0] + forward[0] * 0.55 - right[0] * 0.09, first[1] + forward[1] * 0.55 - right[1] * 0.09, first[2] - 0.2]
        box("fg_near", at, [0.16, 0.16, 0.3], "prop")
    return items


def _subject_at(subject, frame_index):
    return subject["track"][frame_index] if "track" in subject else subject["at"]


def shot_size(fraction):
    """Name for how large a person is: the share of the frame height that a whole body takes."""
    for limit, name in ((0.25, "extreme wide shot"), (0.6, "wide shot"), (1.05, "full shot"), (1.6, "medium-full shot"),
                        (2.4, "medium shot"), (3.6, "medium close-up"), (6.0, "close-up")):
        if fraction < limit:
            return name
    return "extreme close-up"


def _in_frame(point):
    return bool(point) and abs(point[0]) <= 1 and abs(point[1]) <= 1


def framing_checks(plan, aspect):
    """For each still: where each person is in the frame. Pure geometry; it does not test what hides a person."""
    out = {}
    for name, frame in plan["stills"].items():
        sample = plan["camera"]["samples"][frame - 1]
        people = []
        for subject in plan["subjects"]:
            if subject["hidden"]:
                continue
            at = _subject_at(subject, frame - 1)
            head = project([at[0], at[1], at[2] + subject["head_z"]], sample, aspect)
            feet = project([at[0], at[1], at[2] + 0.03], sample, aspect)
            entry = {"id": subject["id"], "head_in_frame": _in_frame(head), "feet_in_frame": _in_frame(feet)}
            if head and feet:
                entry["frame_x"] = r4((head[0] + feet[0]) / 2)
                entry["body_share"] = r4(abs(head[1] - feet[1]) / 2 * subject["height"] / (subject["head_z"] - 0.03))
                entry["shot_size"] = shot_size(entry["body_share"])
                entry["screen_side"] = "left" if entry["frame_x"] < -0.15 else "right" if entry["frame_x"] > 0.15 else "centre"
            to_cam = _norm([sample[0] - at[0], sample[1] - at[1], 0.0])
            face = [math.cos(math.radians(subject["facing_deg"])), math.sin(math.radians(subject["facing_deg"])), 0.0]
            entry["face_to_lens_deg"] = r4(math.degrees(math.acos(max(-1.0, min(1.0, _dot(to_cam, face))))))
            people.append(entry)
        out[name] = people
    return out


def check_notes(plan):
    notes = []
    kind = plan["kind"]
    for name, people in plan["checks"].items():
        for person in people:
            tight = person.get("body_share", 0) >= 1.6 and any(p["head_in_frame"] for p in people)
            if not person["head_in_frame"] and not tight and kind not in ("whip", "montage", "pov", "crane"):
                notes.append(f"{name} still: the head of {person['id']} is outside the frame.")
            if person["head_in_frame"] and person["face_to_lens_deg"] < 20 and kind not in ("overhead", "pov"):
                notes.append(f"{name} still: {person['id']} faces the lens. Move the camera to a three-quarter position.")
    if kind not in ("overhead", "pov", "montage") and any(s[1] > 0.01 for s in plan["camera"]["samples"]):
        notes.append("The camera crosses the action line. Screen direction flips.")
    return notes


def summarise(plan, option, centres):
    samples = plan["camera"]["samples"]
    first, last = samples[0], samples[-1]

    def describe(s, c):
        x, y = s[0] - c[0], s[1] - c[1]
        flat = math.hypot(x, y)
        az = math.degrees(math.atan2(-y, x)) if flat > 1e-6 else 0.0
        return {"height_m": r4(s[2]), "distance_m": r4(flat), "azimuth_deg": r4(az), "lens_mm": r4(s[6]), "roll_deg": r4(s[7])}

    # A camera that travels with the people is measured from the people. Every other camera is measured
    # from the place where the people are at the peak of the action: the middle frame.
    rides, origin = plan["kind"] in ("track", "follow", "oner", "pov"), [0.0, 0.0, 0.0]
    path = sum(math.dist(samples[i][0:3], samples[i + 1][0:3]) for i in range(len(samples) - 1)
               if math.dist(samples[i][0:3], samples[i + 1][0:3]) < 1.0)
    return {"move": plan["kind"], "people": len(plan["subjects"]), "start": describe(first, centres[0] if rides else origin), "end": describe(last, centres[-1] if rides else origin),
            "camera_path_m": r4(path), "placement_words": option.get("placement", ""), "lens_words": option.get("lens", "")}


# --------------------------------------------------------------------------
# The Blender script
# --------------------------------------------------------------------------
def render_script(plan):
    """The self-contained Blender Python script for 1 plan."""
    try:
        runtime = RUNTIME.read_text(encoding="utf-8")
    except OSError as exc:
        raise PrevisError(f"Cannot read {RUNTIME.name}: {exc}")
    if runtime.count(PLAN_MARKER) != 1:
        raise PrevisError(f"{RUNTIME.name} has no plan marker line.")
    text = json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return runtime.replace(PLAN_MARKER, "PLAN = json.loads(" + json.dumps(text, ensure_ascii=True) + ")\n")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Detection
# --------------------------------------------------------------------------
def candidate_paths(environ=None, platform=None):
    environ = os.environ if environ is None else environ
    platform = platform or sys.platform
    paths = []
    if platform == "darwin":
        paths += ["/Applications/Blender.app/Contents/MacOS/Blender",
                  str(Path(environ.get("HOME", "~")) / "Applications/Blender.app/Contents/MacOS/Blender")]
    elif platform.startswith("win"):
        for root in (environ.get("ProgramFiles"), environ.get("ProgramFiles(x86)")):
            if root:
                base = Path(root) / "Blender Foundation"
                try:
                    folders = sorted((p for p in base.iterdir() if p.is_dir()), reverse=True)
                except OSError:
                    folders = []
                paths += [str(folder / "blender.exe") for folder in folders]
    else:
        paths += ["/usr/bin/blender", "/usr/local/bin/blender", "/snap/bin/blender", "/opt/blender/blender",
                  "/var/lib/flatpak/exports/bin/org.blender.Blender"]
    return paths


def find_blender(env_value=None, which=shutil.which, exists=os.path.isfile, environ=None, platform=None):
    """Return (path, source) or (None, reason)."""
    if env_value:
        found = env_value if exists(env_value) else which(env_value)
        if found:
            return found, "the BLENDER variable"
        return None, "The BLENDER variable does not point at a program."
    found = which("blender")
    if found:
        return found, "PATH"
    for path in candidate_paths(environ, platform):
        if exists(path):
            return path, "a standard install folder"
    return None, "No Blender program was found (looked at the BLENDER variable, PATH and the standard install folders)."


def blender_version(binary, run=subprocess.run):
    """Version text such as '5.2.2', or None. Runs ``blender --version`` only: no window opens."""
    try:
        done = run([binary, "--version"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.search(r"Blender (\d+\.\d+(?:\.\d+)?)", (done.stdout or "") + (done.stderr or ""))
    return match.group(1) if match else None


def mcp_socket_open(host=MCP_DEFAULT_HOST, port=MCP_DEFAULT_PORT, connect=socket.create_connection, timeout=0.5):
    """True when something accepts a TCP connection on the Blender MCP add-on port. Sends no data."""
    try:
        connection = connect((host, int(port)), timeout=timeout)
    except (OSError, ValueError):
        return False
    try:
        connection.close()
    except OSError:
        pass
    return True


def detect(env_value=None, host=None, port=None, **hooks):
    """Report the previs route: 'mcp', 'headless' or 'none'."""
    host = host or MCP_DEFAULT_HOST
    port = int(port or MCP_DEFAULT_PORT)
    finder = {k: hooks[k] for k in ("which", "exists", "environ", "platform") if k in hooks}
    binary, source = find_blender(env_value, **finder)
    version = blender_version(binary, hooks.get("run", subprocess.run)) if binary else None
    live = mcp_socket_open(host, port, hooks.get("connect", socket.create_connection))
    if live:
        route, reason = "mcp", f"A Blender MCP add-on answers on {host}:{port}."
    elif binary and version:
        route, reason = "headless", f"Blender {version} runs without a window (found by {source}). No MCP add-on answers on {host}:{port}."
    elif binary:
        route, reason = "none", "A Blender program was found, but it did not report a version."
    else:
        route, reason = "none", source
    return {"route": route, "reason": reason, "blender": binary, "blender_source": source if binary else None,
            "version": version, "mcp": {"host": host, "port": port, "open": live}}


# --------------------------------------------------------------------------
# Running and the manifest
# --------------------------------------------------------------------------
ROLES = ("still_start", "still_mid", "still_end", "plan_overhead", "animatic", "blend")
FILE_NAMES = {"still_start": "still_start.png", "still_mid": "still_mid.png", "still_end": "still_end.png",
              "plan_overhead": "plan_overhead.png", "animatic": "animatic.mp4", "blend": "blocking.blend"}
REQUIRED = ("still_start", "still_mid", "still_end", "plan_overhead")


def option_dir(previs_dir, label):
    return Path(previs_dir) / f"option_{label}"


def write_scripts(doc, previs_dir, only=None, long_edge=DEFAULT_LONG_EDGE):
    """Write blocking.py for each option. Returns [(option, plan, script path)]."""
    ctx = {k: doc.get(k, "") for k in ("subject", "action", "setting", "aspect")}
    out = []
    for option in doc["options"]:
        if only and option["label"] not in only:
            continue
        plan = solve(option, ctx, long_edge)
        folder = option_dir(previs_dir, option["label"])
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "blocking.py"
        path.write_text(render_script(plan), encoding="utf-8")
        out.append((option, plan, path))
    return out


def headless_command(binary, script, out_dir, animatic=True):
    command = [str(binary), "--background", "--factory-startup", "--python-exit-code", "1", "--python", str(script),
               "--", "--out", str(out_dir)]
    if not animatic:
        command.append("--no-animatic")
    return command


def run_headless(binary, script, out_dir, animatic=True, timeout=DEFAULT_TIMEOUT, run=subprocess.run):
    """Run 1 script without a window. Returns (ok, message)."""
    try:
        done = run(headless_command(binary, script, out_dir, animatic), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"Blender did not finish in {timeout} s. It was stopped."
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"Blender did not start: {exc}"
    if done.returncode != 0:
        tail = [line for line in ((done.stdout or "") + (done.stderr or "")).splitlines() if line.strip()][-6:]
        return False, "Blender ended with an error: " + " | ".join(tail)
    return True, "ok"


def mcp_snippet(script, out_dir):
    """Short code for the MCP execute-code tool. It runs the saved script inside the live Blender."""
    return ("import runpy, sys\n"
            f"sys.argv = ['blender', '--', '--out', {str(Path(out_dir).resolve())!r}, '--session']\n"
            f"runpy.run_path({str(Path(script).resolve())!r}, run_name='__main__')\n")


def collect(doc, previs_dir, plans, route, detection, statuses=None, skipped=None):
    """Hash the files that exist and write previs.json. Paths in the manifest are relative to previs_dir."""
    previs_dir = Path(previs_dir)
    statuses = statuses or {}
    entries = []
    for option, plan, script in plans:
        folder = option_dir(previs_dir, option["label"])
        files = []
        for role in ROLES:
            path = folder / FILE_NAMES[role]
            if path.is_file():
                files.append({"role": role, "path": path.relative_to(previs_dir).as_posix(), "bytes": path.stat().st_size,
                              "sha256": sha256_file(path)})
        result = {}
        try:
            result = json.loads((folder / "result.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        have = {f["role"] for f in files}
        status, message = statuses.get(option["label"], (None, None))
        if status is None:
            status = "ok" if all(role in have for role in REQUIRED) else "not_rendered"
        entries.append({
            "label": option["label"], "technique": plan["technique"], "pro_term": plan["pro_term"], "status": status,
            "message": message, "script": script.relative_to(previs_dir).as_posix(), "script_sha256": sha256_file(script),
            "frames": plan["frames"], "fps": plan["fps"], "resolution": plan["resolution"], "summary": plan["summary"],
            "checks": plan["checks"], "notes": plan["notes"], "hidden": result.get("hidden", []),
            "engine": result.get("engine"), "files": files,
        })
    manifest = {"tool": "shot-speak", "schema": SCHEMA, "phrase": doc.get("phrase", ""), "route": route,
                "blender_version": detection.get("version"), "skipped": skipped, "use": USE_RULE, "options": entries}
    previs_dir.mkdir(parents=True, exist_ok=True)
    (previs_dir / "previs.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


USE_RULE = ("A previs frame controls framing, lens, camera path and where people stand. "
            "It never controls the look, the light, the colour or the identity of a person.")


def describe(entry):
    """Plain lines for chat: what the previs measured for 1 option."""
    s, e = entry["summary"]["start"], entry["summary"]["end"]
    lines = [f"Option {entry['label']}: {entry['pro_term']}  [{entry['status']}]",
             f"  Camera start: {s['height_m']:.3g} m high, {s['distance_m']:.3g} m from the group, {s['lens_mm']:.3g} mm.",
             f"  Camera end:   {e['height_m']:.3g} m high, {e['distance_m']:.3g} m from the group, {e['lens_mm']:.3g} mm. "
             f"Path: {entry['summary']['camera_path_m']:.3g} m in {entry['frames'] / entry['fps']:.3g} s."]
    people = entry["checks"].get("mid", [])
    if people:
        lines.append("  Middle frame: " + "; ".join(
            f"{p['id']} {p.get('screen_side', 'outside')}, {p.get('shot_size', 'not in frame')}" for p in people) + ".")
    for item in entry.get("hidden", []):
        lines.append(f"  Hidden: {item}")
    for note in entry["notes"]:
        lines.append(f"  Note: {note}")
    if entry.get("message"):
        lines.append(f"  {entry['message']}")
    for item in entry["files"]:
        lines.append(f"  {item['role']}: {item['path']}")
    return lines
