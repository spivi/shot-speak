#!/usr/bin/env python3
"""shot-speak: plain words in, shot options out.

Subcommands
  detect   Show which image backend is available. Never prints a key.
  plan     Turn a plain-words shot description into 3 to 4 distinct options.
  mock     Show the mock-image prompts and the cost estimate (--dry-run), or
           generate the mock stills after the user confirmed the exact card.
  deslop   Flag AI-slop tells in a prompt and print a rewritten starting point.
  choose   Pick or mix options and write the final shot spec and prompt block.
  blender-detect  Show the route for the optional blocking previs: mcp, headless or none.
  previs   Build a grey-box blocking previs for each option in a local Blender (optional).
  sequence Turn the picked option into several short shots with exact cut times.

Python 3 standard library only. No request leaves the machine unless ``mock``
runs with ``--confirm FINGERPRINT`` for the card that ``--dry-run`` printed.
"""

from __future__ import annotations

import argparse
import base64
import copy
import functools
import hashlib
import http.client
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog as C  # noqa: E402
import previs as P  # noqa: E402

VERSION = "0.2.0"
DEFAULT_COUNT = 4
DEFAULT_MAX_IMAGES = 4
DEFAULT_MAX_USD = 1.00
LABELS = "ABCDEFGH"

# Default OpenAI image model. Change it with SHOTSPEAK_OPENAI_MODEL or --model.
OPENAI_DEFAULT_MODEL = "gpt-image-2.5-flare"
OPENAI_URL = "https://api.openai.com/v1/images/generations"
# Planning estimate per mock still, USD. Not a provider quote. See README "Cost".
OPENAI_EST_USD_PER_IMAGE = 0.07
# Published token rates, USD per 1 million tokens, used only to turn the
# provider's own usage report into a measured cost after a request.
OPENAI_RATES = {"text_input": 5, "image_input": 8, "image_output": 30}

ASPECTS = {"16:9": "1536x864", "9:16": "864x1536", "1:1": "1024x1024", "21:9": "1792x768", "4:3": "1280x960"}
QUALITIES = ("low", "medium", "high")

# The Higgsfield image route. The endpoint id below is recorded in the source workspace as an image endpoint,
# but no image request was sent through it there: the input fields and the price are NOT verified.
# Change the id with SHOTSPEAK_HIGGSFIELD_MODEL. Add input fields with SHOTSPEAK_HIGGSFIELD_EXTRA_INPUT.
HIGGSFIELD_API = "https://api.higgsfield.ai"
HIGGSFIELD_DEFAULT_MODEL = "marketing-studio/image/flare"

BACKENDS = (
    # name, key variable, model variable, default model
    ("openai", "OPENAI_API_KEY", "SHOTSPEAK_OPENAI_MODEL", OPENAI_DEFAULT_MODEL),
    # Second until 1 live image request confirms its endpoint, its input fields and its price. Then it moves to the top.
    ("higgsfield", "HF_KEY", "SHOTSPEAK_HIGGSFIELD_MODEL", HIGGSFIELD_DEFAULT_MODEL),
    ("fal", "FAL_KEY", "SHOTSPEAK_FAL_MODEL", None),
    ("replicate", "REPLICATE_API_TOKEN", "SHOTSPEAK_REPLICATE_MODEL", None),
)

# Names that must never reach a generator prompt: model and product names,
# film and franchise names, studio and director names. Describe the look.
BANNED_NAMES = [
    "sora", "kling", "seedance", "veo", "runway", "midjourney", "dall-e", "dalle", "gpt", "openai", "chatgpt",
    "stable diffusion", "sdxl", "hailuo", "pika labs", "luma ai", "imagen", "firefly", "nano banana", "gemini",
    "replicate", "fal.ai", "unreal engine", "octane", "the matrix", "matrix", "marvel", "disney", "pixar",
    "star wars", "netflix", "john wick", "spider-man", "spiderman", "batman", "superman", "avengers", "anime studio",
    "harry potter", "james bond", "mission impossible", "blade runner", "tarantino", "wes anderson", "nolan",
    "kubrick", "spielberg", "fincher", "villeneuve", "scorsese", "michael bay", "zack snyder", "wong kar-wai",
    "imax", "arri", "alexa", "red camera", "go-pro", "gopro", "iphone", "tiktok", "instagram", "youtube",
    "nike", "adidas", "coca-cola", "pepsi", "lego", "tesla", "apple",
]
ALIASES_FILE = Path(__file__).resolve().parent / "look_aliases.json"


def load_aliases(path=ALIASES_FILE):
    """{look id: {"names": [...], "words": [...]}}. Names are titles and people. Words are genre words."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))["looks"]
    except (OSError, ValueError, KeyError):
        return {}


LOOK_ALIASES = load_aliases()
# A name with a leading ~ is also a common word. It is recognised only after a cue such as "like".
LOOK_NAMES = sorted({n for entry in LOOK_ALIASES.values() for n in entry["names"] if not n.startswith("~")})
_BANNED_RE = re.compile(r"(?<![a-z0-9])(" + "|".join(re.escape(n) for n in sorted(set(BANNED_NAMES) | set(LOOK_NAMES), key=len, reverse=True))
                        + r")(?![a-z0-9])", re.I)
_CUE = r"(?:like|as in|style of|styled? like|inspired by|from|out of|a la|feel of|look of|vibe of|think)"
_UNKNOWN_REF_RE = re.compile(r"\b(?:like|as in|style of|inspired by|a la)\s+(?:the |a |an |that |those )?"
                             r"((?:[A-Z0-9][\w'.:-]*)(?:\s+(?:of|the|and|in|a|to|[A-Z0-9][\w'.:-]*))*)")
_PRIVATE_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|https?://\S+|\bfile://\S+|\bdata:[\w/+.-]+[;,]\S*|(?:/Users/|/home/|~/|[A-Z]:\\)\S+"
                         r"|\b(?:sk|key|tok|r8|fal|hf)[-_][A-Za-z0-9_-]{16,}")
# Negation scope: a negation word negates the rest of its clause. "Avoid:" negates the rest of its line.
_NEGATION_RE = re.compile(r"(?<![\w-])(no|not|never|avoid|without|nobody|nothing|none|neither|nor|don't|don’t|do not|doesn't|"
                          r"does not|instead of|rather than)(?![\w-])", re.I)
_AVOID_HEAD_RE = re.compile(r"\b(avoid|negative prompt|negative|do not include|don't include)\s*:", re.I)
_CLAUSE_END_RE = re.compile(r"[.;:!?,\n]+|\s(?:but|while|whereas|except|unless|apart from|other than|outside|save for)\s", re.I)
# An exception after a negation ("no slow motion except at the peak") makes the negation partial: it forbids nothing whole.
_EXCEPTION_RE = re.compile(r"\b(except|unless|apart from|other than|outside|save for|only (at|in|for|on))\b", re.I)
# A shot marker starts a unit that ends at the next marker or the end of its line. Text outside a shot applies to all.
_SHOT_MARK_RE = re.compile(r"(?im)^\s*\d+\.\s|\bshot\s*\d+\s*[:.)-]")
_SENTENCE_END_RE = re.compile(r"[.;!?\n]+")
_ON_PURPOSE_RE = re.compile(r"\b(on purpose|deliberate(ly)?|intentional(ly)?|by design|as a (stylistic|creative|deliberate) choice)\b", re.I)


class Refusal(Exception):
    """A request the tool will not run. The message is safe to print."""


# --------------------------------------------------------------------------
# Environment and backend detection
# --------------------------------------------------------------------------
def parse_env_file(path):
    values = {}
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return values
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:]
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        if key.strip() and value:
            values[key.strip()] = value
    return values


def git_ignored(path):
    """True, False, or None when the file is not in a Git work tree."""
    try:
        inside = subprocess.run(["git", "-C", str(Path(path).parent), "rev-parse", "--is-inside-work-tree"],
                                capture_output=True, text=True, timeout=5)
        if inside.returncode != 0:
            return None
        done = subprocess.run(["git", "-C", str(Path(path).parent), "check-ignore", "-q", str(path)],
                              capture_output=True, timeout=5)
        return done.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return None


def load_env(cwd=".", env_file=None, environ=None):
    """Return {NAME: (value, source)}. Order: process environment, .env.local, .env.

    ``env_file`` replaces the two default files.
    """
    environ = os.environ if environ is None else environ
    found = {name: (value, "process environment") for name, value in environ.items() if value}
    if "HF_KEY" not in found and "HF_API_KEY" in found and "HF_API_SECRET" in found:
        found["HF_KEY"] = (found["HF_API_KEY"][0] + ":" + found["HF_API_SECRET"][0], "process environment")
    files = [Path(env_file)] if env_file else [Path(cwd) / ".env.local", Path(cwd) / ".env"]
    for path in files:
        for name, value in parse_env_file(path).items():
            found.setdefault(name, (value, path.name))
    return found


def env_value(env, name, default=None):
    return env[name][0] if name in env else default


def detect_backends(env):
    """All backends with a key, in priority order."""
    out = []
    for name, key_var, model_var, default_model in BACKENDS:
        if key_var in env:
            out.append({"name": name, "key_var": key_var, "source": env[key_var][1],
                        "model": env_value(env, model_var, default_model), "model_var": model_var})
    return out


def select_backend(env, prefer=None, model=None, require_key=True):
    """Pick the backend. ``prefer`` can be a backend name, 'host' or 'text'.

    With ``require_key=False`` (a dry run) a named backend is returned without a key.
    """
    if prefer in ("host", "text"):
        return {"name": prefer, "key_var": None, "source": None, "model": None, "model_var": None}
    found = detect_backends(env)
    if prefer:
        match = [b for b in found if b["name"] == prefer]
        if not match:
            known = [b[0] for b in BACKENDS]
            if prefer not in known:
                raise Refusal(f"Unknown backend '{prefer}'. Use one of: {', '.join(known)}, host, text.")
            name, key_var, model_var, default_model = [b for b in BACKENDS if b[0] == prefer][0]
            if not require_key:
                return {"name": name, "key_var": key_var, "source": None, "model_var": model_var,
                        "model": model or env_value(env, model_var, default_model)}
            raise Refusal(f"Backend '{prefer}' needs {key_var} in the environment or in .env.local.")
        found = match
    if not found:
        return {"name": "text", "key_var": None, "source": None, "model": None, "model_var": None}
    backend = dict(found[0])
    if model:
        backend["model"] = model
    return backend


def secrets_of(env):
    secrets = [env[b[1]][0] for b in BACKENDS if b[1] in env]
    return secrets + [part for s in secrets for part in s.split(":") if ":" in s]


def redact(text, secrets):
    text = str(text)
    for secret in secrets:
        if secret and len(secret) >= 4:
            text = text.replace(secret, "[REDACTED]")
    return re.sub(r"(Bearer|Key|Token)\s+[A-Za-z0-9._\-]{8,}", r"\1 [REDACTED]", text)


# --------------------------------------------------------------------------
# Lint: names, private data, AI-slop tells
# --------------------------------------------------------------------------
def banned_names(text):
    return sorted({m.group(1).lower() for m in _BANNED_RE.finditer(text or "")})


def private_data(text):
    return _PRIVATE_RE.findall(text or "")


def lint_prompt(text):
    """Problems that stop a prompt from being sent or printed as final."""
    problems = [f"names a product, model or protected title: '{n}'. Describe the look or the shape instead." for n in banned_names(text)]
    if private_data(text):
        problems.append("contains an email address, a URL, a file path or a key. Remove it.")
    return problems


def segments(text):
    """Cut ``text`` into consecutive parts: (part, kind, on_purpose). Joined, the parts give ``text`` back.

    ``kind`` is "ask" (a clause or the start of a clause that asks for something), "forbid" (from a negation word
    to the end of its clause, or everything after "Avoid:" on its line) or "gap" (the punctuation between clauses).
    ``on_purpose`` is True when the sentence of the part says "on purpose", "deliberately" or a similar marker.
    """
    out = []
    for line in re.split(r"(?<=\n)", text or ""):
        head = _AVOID_HEAD_RE.search(line)
        body, tail = (line[:head.start()], line[head.start():]) if head else (line, "")
        at = 0
        for end in [m for m in _CLAUSE_END_RE.finditer(body)] + [None]:
            clause = body[at:end.start() if end else len(body)]
            sentence_end = _SENTENCE_END_RE.search(body, at)
            sentence_start = max((m.end() for m in _SENTENCE_END_RE.finditer(body, 0, at)), default=0)
            purpose = bool(_ON_PURPOSE_RE.search(body[sentence_start:sentence_end.start() if sentence_end else len(body)]))
            negation = _NEGATION_RE.search(clause)
            if negation:
                out += [(clause[:negation.start()], "ask", purpose), (clause[negation.start():], "forbid", purpose)]
            else:
                out.append((clause, "ask", purpose))
            if end:
                out.append((end.group(0), "gap", False))
                at = end.end()
        if tail:
            out.append((tail, "forbid", False))
    return [part for part in out if part[0]]


def _tell_matches(tell, parts):
    """(index of the part, match) for each match of the tell's patterns in the parts that ask for something."""
    found = []
    for index, (part, kind, _purpose) in enumerate(parts):
        if kind != "ask" or (tell.get("needs") and not re.search(tell["needs"], part, re.I)):
            continue
        for pattern in tell.get("patterns", []):
            found += [(index, m) for m in re.finditer(pattern, part, re.I)]
    return sorted(found, key=lambda f: (f[0], f[1].start()))


def _spared(tell, match_text, intended):
    """True when the user intends this technique and this piece of evidence belongs to it."""
    return intended and (not tell.get("spares") or bool(re.fullmatch(tell["spares"], match_text.strip(" ,"), re.I)))


def _shot_of(text, at):
    """The start of the shot marker that holds position ``at``, or None for text that applies to every shot."""
    marks = [m.start() for m in _SHOT_MARK_RE.finditer(text, 0, at + 1)]
    return marks[-1] if marks and "\n" not in text[marks[-1]:at] else None


def _forbidden(tell, parts, text, matches):
    """True when the prompt forbids what a tell asks for: an unqualified negation of the same thing in the same shot
    (or in text that applies to every shot). "No slow motion except at the peak" is qualified, so it forbids nothing whole."""
    starts, at = [], 0
    for part, _kind, _purpose in parts:
        starts.append(at)
        at += len(part)
    asked = {_shot_of(text, starts[index] + m.start()) for index, m in matches}
    for index, (part, kind, _purpose) in enumerate(parts):
        if kind != "forbid" or not re.search(tell["forbids"], part, re.I):
            continue
        sentence_end = _SENTENCE_END_RE.search(text, starts[index])
        if _EXCEPTION_RE.search(text, starts[index], sentence_end.start() if sentence_end else len(text)):
            continue
        shot = _shot_of(text, starts[index])
        if shot is None or None in asked or shot in asked:
            return True
    return False


def scan(text, check_missing=False, context=""):
    """The AI-slop tells in a prompt. Returns (flagged, kept), 2 lists of tell dicts with 'evidence'.

    Only the parts that ask for something count; "no fog" asks for nothing. A tell is kept, not flagged, when
    the user clearly intends it: its intent words are in ``text`` or ``context`` (the user's own words), or its
    sentence says "on purpose". A flagged tell that the prompt also forbids is marked 'contradiction'.
    The test is words only. It does not understand the scene, so a kept tell says why it was kept.
    """
    parts = segments(text)
    words = f"{text or ''} . {context or ''}"
    asked = " . ".join(p for p, kind, _ in parts if kind == "ask")
    flagged, kept = [], []
    for tell in C.SLOP_TELLS:
        base = {k: tell[k] for k in ("id", "category", "tell", "why", "fix", "fine_when")}
        matches, intent = _tell_matches(tell, parts), None
        if matches and tell.get("intent"):  # compiled only when needed: most prompts hit few tells
            intent = re.search(tell["intent"], words, re.I)
        live, spared = [], []
        for index, match in matches:
            (spared if _spared(tell, match.group(0), bool(intent) or parts[index][2]) else live).append(match.group(0))
        if live and tell["id"] == "default_medium" and re.search(
                r"profile|three[- ]quarter|side[- ]on|from (the side|behind|below|above)|over[- ]the[- ]shoulder|floor|overhead", asked, re.I):
            live = []
        if live:
            hit = {**base, "evidence": live[0]}
            if tell.get("forbids") and _forbidden(tell, parts, text or "", matches):
                hit["contradiction"] = True
            flagged.append(hit)
        elif spared:
            kept.append({**base, "evidence": spared[0], "because": intent.group(0) if intent else "on purpose"})
        elif check_missing and tell.get("missing") and not re.search(tell["missing"], text or "", re.I):
            if tell.get("supplied") and re.search(tell["supplied"], words, re.I):
                kept.append({**base, "evidence": "(not stated)", "because": "a reference gives it"})
            else:
                flagged.append({**base, "evidence": "(not stated)"})
    return flagged, kept


def slop_tells(text, check_missing=False, context=""):
    """The flagged AI-slop tells in a prompt (see ``scan``)."""
    return scan(text, check_missing, context)[0]


def finding(hit):
    """1 line of advice for a flagged tell: what was found, the fix, and when the technique is right."""
    lead = "Asked for and also forbidden: " if hit.get("contradiction") else ""
    return f"{lead}{hit['tell']} ('{hit['evidence']}'). {hit['fix']} Fine when: {hit['fine_when']}."


def anti_slop_check(option, context=""):
    """Advice for 1 option. Returns a list of findings. A finding is advice: it never blocks a request.

    ``context`` is the user's own words (the phrase, the subject, the action, the place). It can make a tell a choice.
    An option can also list tell ids in ``on_purpose`` to keep them.
    """
    findings = []
    on_purpose = set(option.get("on_purpose") or [])
    text = " ".join(str(option.get(k, "")) for k in ("movement", "placement", "still", "video_snippet", "image_prompt"))
    light = option.get("light", {}).get("prompt", "")
    for hit in slop_tells(text + " . " + light, context=context):
        if hit["id"] != "vague_cinematic" and hit["id"] not in on_purpose:
            findings.append(finding(hit))
    lens = re.findall(r"\d+", str(option.get("lens", "")))
    placement = str(option.get("placement", "")).lower()
    angled = re.search(r"side|profile|three[- ]quarter|behind|floor|above|overhead|knee|waist|hip|shoulder", placement)
    if lens and all(35 <= int(n) <= 50 for n in lens) and re.search(r"chest|eye", placement) and not angled \
            and "default_lens" not in on_purpose:
        findings.append("The 35 to 50 mm default at chest or eye height. " + C.SLOP_BY_ID["default_lens"]["fix"])
    if not lens:
        findings.append("No lens stated. " + C.SLOP_BY_ID["missing_lens"]["fix"])
    if not option.get("light", {}).get("prompt"):
        findings.append("No light source stated. " + C.SLOP_BY_ID["missing_light"]["fix"])
    if not option.get("speed", {}).get("prompt"):
        findings.append("No speed stated. " + C.SLOP_BY_ID["missing_speed"]["fix"])
    if "orbit_full" not in on_purpose:
        for degrees in re.findall(r"(\d{2,3}) degrees", str(option.get("movement", ""))):
            if int(degrees) >= 180:
                findings.append(f"An arc of {degrees} degrees. " + C.SLOP_BY_ID["orbit_full"]["fix"])
    if option.get("grade", {}).get("key") == "teal_orange" and not option.get("grade_on_purpose") \
            and "teal_orange_default" not in on_purpose:
        findings.append("Teal and orange by default. " + C.SLOP_BY_ID["teal_orange_default"]["fix"])
    return findings


@functools.lru_cache(maxsize=256)
def _user_choices(phrase, subject, action, setting):
    sent = " . ".join((subject, action, setting))
    asked = {h["id"] for h in sum(scan(sent, context=phrase), [])}  # the prompt itself will ask for these
    chosen = {h["id"] for h in scan(phrase, context=sent)[1]}  # the user's words ask for these on purpose
    words = f"{phrase} . {sent}"
    present = {t["id"] for t in C.SLOP_TELLS if "avoid_kept" in t and re.search(t["intent"], words, re.I)}  # fog, rain in the place
    return frozenset(asked | chosen | present)


def user_choices(ctx):
    """Tell ids whose avoid clause would contradict the user: the subject, the action or the place asks for the
    technique, the user's words ask for it on purpose, or the place holds the thing (fog, rain)."""
    return _user_choices(*(str(ctx.get(k) or "") for k in ("phrase", "subject", "action", "setting")))


def avoid_clauses(tell_ids, choices=frozenset()):
    """The avoid clauses of the tells, once each. A tell in ``choices`` gets its 'avoid_kept' clause, or none."""
    seen, out = set(), []
    for tell_id in tell_ids:
        tell = C.SLOP_BY_ID[tell_id]
        clause = tell.get("avoid_kept", "") if tell_id in choices else tell["avoid"]
        if clause and tell_id not in seen:
            seen.add(tell_id)
            out.append(clause)
    return out


# --------------------------------------------------------------------------
# "Like a film": a named look becomes a recipe with no name in it
# --------------------------------------------------------------------------
def _alias_pattern(alias):
    ambiguous = alias.startswith("~")
    body = re.escape(alias.lstrip("~")).replace(r"\ ", r"\s+")
    lead = rf"(?:{_CUE})\s+(?:the\s+|a\s+|an\s+|that\s+)?" if ambiguous else ""
    return rf"(?<![a-z0-9])({lead})({body})(?![a-z0-9])"


def find_look(phrase):
    """Return (look id or None, the phrase with every name removed, True when a reference is unknown).

    The longest alias wins. A recognised name is replaced with the neutral name of its look.
    A name that is not in the lookup is replaced with a neutral marker: this tool never guesses a recipe.
    """
    hits = []
    for look_id, entry in LOOK_ALIASES.items():
        for alias in entry["names"] + entry["words"]:
            match = re.search(_alias_pattern(alias), phrase, re.I)
            if match:
                hits.append((len(alias.lstrip("~")), -match.start(), look_id))
    look_id = max(hits)[2] if hits else None
    text = phrase
    for other_id, entry in LOOK_ALIASES.items():
        neutral = "the " + C.LOOKS[other_id]["name"].lower() + " look"
        for alias in sorted(entry["names"], key=len, reverse=True):
            text = re.sub(_alias_pattern(alias) + r"(?:'s)?(?:\s+(?:movies?|films?|style|look))?", lambda m: m.group(1) + neutral, text, flags=re.I)
    text = re.sub(r"\b(?:the|a|an) the\b", "the", text, flags=re.I)
    text = _BANNED_RE.sub("a named reference", text)
    unknown = False
    if look_id is None:
        match = _UNKNOWN_REF_RE.search(text)
        if match and not match.group(1).lower().startswith("a named reference"):
            unknown = True
            text = text[:match.start(1)] + "a reference this tool does not know" + text[match.end(1):]
        elif "a named reference" in text:
            unknown = True
    return look_id, text, unknown


# --------------------------------------------------------------------------
# Interpretation: plain words -> techniques
# --------------------------------------------------------------------------
def interpret(phrase):
    """Score techniques for a phrase. Returns (ordered ids, matched notes)."""
    scores, notes, order = {}, [], {}
    for index, (pattern, weight, ids, note, _examples) in enumerate(C.PHRASE_RULES):
        if re.search(r"\b(?:" + pattern + ")", phrase, re.I):
            notes.append(note)
            for position, tech in enumerate(ids):
                scores[tech] = scores.get(tech, 0) + weight * (len(ids) - position)
                order.setdefault(tech, (index, position))
    ranked = sorted(scores, key=lambda t: (-scores[t], order[t]))
    return ranked, notes


def vagueness(phrase):
    """Deterministic test: do the words name a picture, or only a mood? Returns (vague, reasons)."""
    reasons = []
    ranked, _notes = interpret(phrase)
    visual, _ = interpret(re.sub(r"\b(?:" + C.MOOD_WORDS + r")\b", " ", phrase, flags=re.I))
    moods = sorted({m.group(0).lower() for m in re.finditer(r"\b(?:" + C.MOOD_WORDS + r")\b", phrase, re.I)})
    if not ranked:
        reasons.append("No word names a camera move, a camera position, a speed or a known look.")
    elif not visual:
        reasons.append("The words name a mood (" + ", ".join(moods) + "), not a picture. A mood has many possible shots.")
    if len(moods) >= 2 and not visual:
        reasons.append("2 or more moods pull in different directions. The look must be found with the user.")
    return bool(reasons), reasons


def distinct_families(candidates, count, chosen=()):
    """Add techniques from ``candidates``, in order, until ``count`` are chosen. Each one has its own family."""
    chosen = list(chosen)
    families = {C.TECHNIQUES[tech]["family"] for tech in chosen}
    for tech in candidates:
        family = C.TECHNIQUES[tech]["family"]
        if len(chosen) < count and family not in families:
            chosen.append(tech)
            families.add(family)
    return chosen


def pick_techniques(phrase, count=DEFAULT_COUNT):
    ranked, notes = interpret(phrase)
    return distinct_families(ranked + [t for t in C.FALLBACK if t not in ranked], count), notes, bool(ranked)


def default_subject(phrase):
    if re.search(r"\b(them|they|two|both|couple|pair|friends|kids|people)\b", phrase, re.I):
        return "two stand-in performers in plain dark clothes"
    return "one stand-in performer in plain dark clothes"


def default_action(phrase):
    if re.search(r"mid[- ]?air|jump|leap|flip|in the air|airborne", phrase, re.I):
        return "at the top of a jump"
    if re.search(r"run|chase|sprint", phrase, re.I):
        return "running at full speed"
    if re.search(r"walk|enter|arriv", phrase, re.I):
        return "walking in with purpose"
    return "in the middle of the action"


def lens_look(lens):
    numbers = re.findall(r"\d+", lens)
    if "zooming" in lens and len(numbers) == 2:
        end = next((k for k in C.LENSES if k.split()[0] == numbers[1]), None)
        return f"zoom lens caught at its long end, {numbers[1]} mm: {C.LENSES[end] if end else 'compressed depth'}"
    if "alternating" in lens:
        return C.LENSES["18 mm"]
    first = next((key for key in C.LENSES if key.split()[0] in numbers), "35 mm")
    return C.LENSES[first]


def _airborne(option, ctx):
    """True when bodies leave the ground or time slows: the cases where generators make people float."""
    return option["speed"]["key"] in ("slow_motion", "frozen_moment", "speed_ramp", "ramp_on_contact") or bool(
        re.search(r"jump|leap|flip|air|fall|dive|vault|trick|throw", ctx.get("action", ""), re.I))


# The catalogue words of a technique (``still``, ``snippet``) repeat some of its decisions. When a round, a mix or an
# edit changes 1 of those decisions, the words that name the old value are removed, so a prompt never says 2 things.
_HEIGHT_WORDS = re.compile(r",?\s*\b(at|from) (the subject's |the character's |their )?(own|eye|waist|hip|shoulder|knee|chest) (height|level)\b"
                           r"|,?\s*\b(on the floor|at floor level|from directly above|from high above)\b", re.I)
_LENS_WORDS = re.compile(r",?\s*\b(on |with |from )?(an? )?(ultra-wide|wide|long) lens\b", re.I)
_SPEED_WORDS = re.compile(r"\b(time almost stops while |in real time )|;?\s*real time into the move, a short ramp to slow motion at the peak, "
                          r"then back to real time", re.I)


def option_wording(option, field):
    """The option's ``still`` or ``snippet``, true to its current decisions. None when its camera move changed:
    then the prompt is built from the decisions alone. Words that the user wrote are returned as they are."""
    text, tech = option[field], C.TECHNIQUES.get(option.get("technique"))
    if not tech or text != tech[field]:
        return text
    if option.get("movement") != tech["movement"]:
        return None
    for changed, words in ((option.get("placement") != tech["placement"], _HEIGHT_WORDS), (option.get("lens") != tech["lens"], _LENS_WORDS),
                           (option["speed"].get("key") != tech["speed"], _SPEED_WORDS)):
        if changed:
            text = words.sub("", text)
    return text


def _placement_changed(option):
    tech = C.TECHNIQUES.get(option.get("technique"))
    return bool(tech) and option.get("placement") != tech["placement"] and option.get("snippet") == tech["snippet"]


def build_image_prompt(option, ctx):
    tech = C.TECHNIQUES.get(option.get("technique"), {})
    tells = list(tech.get("slop_avoids", [])) + C.STILL_BASE_AVOID
    if _airborne(option, ctx):
        tells.append("floating_bodies")
    if option["light"]["key"] in ("hard_backlight", "silhouette_rim", "low_side_sun"):
        tells.append("flare_spam")
    if option["light"]["key"] in ("overcast_soft", "high_key"):
        tells = [t for t in tells if t != "soft_glow"]
    choices = user_choices(ctx)
    camera = option_wording(option, "still") or f"{option['pro_term']}, the frame at the middle of the shot"
    if option.get("technique") == "pov":
        faces = ["FACES: no face of the point-of-view character is visible."]
    elif "eyes_to_lens" in choices:
        faces = []  # the user's words decide where the faces look
    else:
        faces = ["FACES: turned away from the lens, in profile, three-quarter or from behind."]
    film = C.MEDIUMS[ctx.get("medium") or "live_action"]["film"]
    lines = [
        f"A single still frame from {film}, {ctx['aspect']} frame. A storyboard-grade production mock that shows framing, lens, light and colour.",
        f"SUBJECT: {ctx['subject']} {ctx['action']}, in {ctx['setting']}. Generic stand-in figures, not a likeness of any real person.",
        f"CAMERA: {camera}. Camera placement: {option['placement']}.",
        f"LENS: {option['lens']}; {lens_look(option['lens'])}.",
        f"LIGHT: {option['light']['prompt']}.",
        f"COLOUR: {option['grade']['prompt']}.",
        f"MOMENT: {option['speed']['still']}.",
    ] + ([f"LOOK: {option['look_clause']}."] if option.get("look_clause") else []) + faces + [
        "AVOID: " + "; ".join(avoid_clauses(tells, choices)) + ".",
        "One frame only: no collage, no split screen, no text, no captions, no logos, no watermark, no border.",
    ]
    return medium_text("\n".join(lines), ctx)


def build_video_snippet(option, ctx):
    tech = C.TECHNIQUES.get(option.get("technique"), {})
    tells = list(tech.get("slop_avoids", [])) + C.VIDEO_BASE_AVOID
    if option["speed"]["key"] == "real_time":
        tells.append("slowmo_everywhere")
    if not _airborne(option, ctx):
        tells = [t for t in tells if t != "floating_bodies"]
    template = option_wording(option, "snippet")
    if template is None:
        template = "{subject} {action}; " + option["movement"] + "; camera " + option["placement"]
    elif _placement_changed(option):
        template += "; camera " + option["placement"]
    body = template.format(subject=ctx["subject"], action=ctx["action"])
    body = body[0].upper() + body[1:]
    look = f"; {option['look_clause']}" if option.get("look_clause") else ""
    return medium_text(f"{body}; {option['lens']} lens; {option['light']['prompt']}; {option['grade']['prompt']}; "
                       f"{option['speed']['prompt']}{look}. Avoid: {'; '.join(avoid_clauses(tells, user_choices(ctx)))}.", ctx)


# The generated prompts are derived from the decisions of an option. ``prompt_basis`` records what they were built
# from, so that a later run can tell a stale prompt (the decisions changed: rebuild it) from a hand edit (keep it).
PROMPT_FIELDS = ("image_prompt", "video_snippet")
PROMPT_INPUTS = ("technique", "pro_term", "movement", "placement", "lens", "still", "snippet", "light", "grade", "speed", "look_clause")


def doc_ctx(doc, action=None):
    ctx = {k: doc.get(k, "") for k in ("phrase", "subject", "action", "setting", "aspect")}
    if action:
        ctx["action"] = action
    if doc.get("medium"):
        if doc["medium"] not in C.MEDIUMS:
            raise Refusal(f"Unknown medium '{doc['medium']}'. Use one of: {', '.join(C.MEDIUMS)}.")
        ctx["medium"] = doc["medium"]
    return ctx


def detect_medium(words):
    """The visual medium that the user's words name: a key of C.MEDIUMS. Live action when the words name none."""
    return next((key for key, medium in C.MEDIUMS.items() if re.search(medium["detect"], words or "", re.I)), "live_action")


def medium_text(text, ctx):
    """A prompt in the words of its medium: the phrases that hold only for a camera on a real set are replaced."""
    for old, new in C.MEDIUMS[ctx.get("medium") or "live_action"]["swap"]:
        text = text.replace(old, new)
    return text


def _digest(value):
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _inputs_digest(option, ctx):
    keys = ("phrase", "subject", "action", "setting", "aspect") + (("medium",) if ctx.get("medium") else ())
    return _digest([{k: option.get(k) for k in PROMPT_INPUTS}, {k: ctx.get(k, "") for k in keys}])


def is_custom(option, field):
    """True when the user edited a generated prompt by hand after the tool wrote it."""
    basis = option.get("prompt_basis") if isinstance(option.get("prompt_basis"), dict) else {}
    return bool(option.get(field) and basis.get(field) and basis[field] != _digest(option[field]))


def set_prompts(option, ctx, notes=None):
    """Build the image prompt and the video prompt from the option's decisions. A hand edit is kept while the
    decisions it was made for stay the same. A hand edit whose decisions changed later is refused."""
    basis = option.get("prompt_basis") if isinstance(option.get("prompt_basis"), dict) else {}
    inputs = _inputs_digest(option, ctx)
    custom = [f for f in PROMPT_FIELDS if is_custom(option, f)]
    if custom and basis.get("inputs") != inputs:
        raise Refusal(f"Option {option.get('label')}: {custom[0]} was edited by hand, and its decisions changed after that edit. "
                      f"Delete {custom[0]} to rebuild it from the decisions, or undo the change of the decisions.")
    built = {"image_prompt": build_image_prompt(option, ctx), "video_snippet": build_video_snippet(option, ctx)}
    for field, text in built.items():
        if field in custom:
            continue
        if notes is not None and option.get(field) and not basis and option[field] != text:
            notes.append(f"Option {option.get('label')}: the saved {field} did not match its decisions. It was rebuilt from them.")
        option[field] = text
    option["prompt_basis"] = {"inputs": inputs, **{f: basis[f] if f in custom else _digest(built[f]) for f in PROMPT_FIELDS}}


# The place and the action can name the light. The first cue that matches gives the lights that fit the scene.
LIGHT_CUES = [
    (r"candle|campfire|fireplace|bonfire|torch(es)?\b|lantern", ["firelight"]),
    (r"moon", ["moonlight", "practicals_night", "silhouette_rim"]),
    (r"night|midnight|after dark|neon|street ?lamp", ["practicals_night", "moonlight", "top_pool", "silhouette_rim", "blade_of_light", "firelight"]),
    (r"sunset|sunrise|dusk|dawn|golden hour|low sun|evening", ["hard_backlight", "low_side_sun", "silhouette_rim", "blade_of_light"]),
    (r"overcast|grey day|gray day|cloud|rain|fog|snow", ["overcast_soft", "soft_window"]),
    (r"dark (room|kitchen|hall|corridor|cellar|garage|bar|house)|basement|cellar", ["top_pool", "blade_of_light", "practicals_night", "soft_window", "firelight"]),
]


def scene_lights(ctx):
    text = f"{ctx.get('setting', '')} {ctx.get('action', '')}"
    for pattern, lights in LIGHT_CUES:
        if re.search(pattern, text, re.I):
            return lights
    return []


def _resolve(kind, table, tech, used, fits=(), lead=False):
    first, second = tech[kind]
    fitting = [k for k in (first, second) if k in fits]
    if lead and fits and not fitting:
        key = fits[0]  # the recommended option takes the light that the scene names
    elif fitting:
        key = next((k for k in fitting if k not in used), fitting[0])
    else:
        key = second if first in used and second not in used else first
    used.add(key)
    return {"key": key, "name": table[key]["name"], "plain": table[key]["plain"], "prompt": table[key]["prompt"]}


def build_options(phrase, subject=None, action=None, setting=None, aspect="16:9", count=DEFAULT_COUNT, techniques=None):
    if aspect not in ASPECTS:
        raise Refusal(f"Unknown aspect '{aspect}'. Use one of: {', '.join(ASPECTS)}.")
    if not 3 <= count <= 4:
        raise Refusal("Use 3 or 4 options.")
    notes, matched = [], True
    look_id, phrase, unknown_reference = find_look(phrase)
    look = C.LOOKS.get(look_id)
    if techniques:
        unknown = [t for t in techniques if t not in C.TECHNIQUES]
        if unknown:
            raise Refusal(f"Unknown technique: {', '.join(unknown)}. Known: {', '.join(sorted(C.TECHNIQUES))}.")
        if len(set(techniques)) != len(techniques) or not 3 <= len(techniques) <= 4:
            raise Refusal("Give 3 or 4 different techniques.")
        chosen = list(techniques)
        notes = interpret(phrase)[1]
    else:
        chosen, notes, matched = pick_techniques(phrase, count)
        if look:  # the look that the user named is option A; B to D are different ideas
            chosen = distinct_families([look["technique"]] + look["also"] + chosen, count)
            matched = True
    ctx = {"phrase": phrase, "subject": subject or default_subject(phrase), "action": action or default_action(phrase),
           "setting": setting or "a plain, worn, uncluttered place", "aspect": aspect}
    medium = detect_medium(" . ".join((phrase, subject or "", action or "", setting or "")))
    if medium != "live_action":  # live action is the default and leaves no trace in the files
        ctx["medium"] = medium
        notes = notes + [f"The medium is {C.MEDIUMS[medium]['name'].lower()}, from your words. The prompts describe it in that medium."]
    for field in ("subject", "action", "setting"):
        problems = lint_prompt(ctx[field])
        if problems:
            raise Refusal(f"The {field} {problems[0]}")
    used_lights, used_grades, options = set(), set(), []
    anchored = bool(look) and chosen[0] == look["technique"]
    fits = scene_lights(ctx)
    for index, tech_id in enumerate(chosen):
        tech = C.TECHNIQUES[tech_id]
        if anchored and index == 0:
            tech = dict(tech, light=(look["light"], look["light"]), grade=(look["grade"], look["grade"]))
        speed = C.SPEEDS[tech["speed"]]
        option = {
            "label": LABELS[index], "technique": tech_id, "pro_term": tech["pro_term"], "plain": tech["plain"],
            "movement": tech["movement"], "placement": tech["placement"],
            "lens": tech["lens"], "lens_why": tech["lens_why"],
            "light": _resolve("light", C.LIGHTS, tech, used_lights, fits, lead=index == 0 and not anchored),
            "grade": _resolve("grade", C.GRADES, tech, used_grades),
            "speed": {"key": tech["speed"], "name": speed["name"], "plain": speed["plain"],
                      "prompt": speed["prompt"], "still": speed["still"]},
            "duration": tech["duration"], "feel": tech["feel"], "when": tech["when"], "risks": list(tech["risks"]),
            "still": tech["still"], "snippet": tech["snippet"],
            "slop_avoided": [C.SLOP_BY_ID[t]["tell"] for t in tech["slop_avoids"][:2]],
            "topdown": tech["topdown"], "frame": tech["frame"],
            "recommended": index == 0,
        }
        if anchored and index == 0:
            option.update({"look_id": look_id, "look_name": look["name"], "look_clause": look["clause"], "look_makes": list(look["makes"])})
            if look["grade"] == "teal_orange":
                option["grade_on_purpose"] = True
            option["recommended_because"] = f"It is the look you named, as decisions: {look['name'].lower()}. {look['makes'][0]}"
        elif index == 0:
            option["recommended_because"] = ("It is the closest match to your words. Best for: " + tech["when"][0].lower() + tech["when"][1:]
                                             if matched else "It is the most useful general answer. Tell me more about the feeling you want.")
        set_prompts(option, ctx)
        options.append(option)
    slow = [o["label"] for o in options if o["speed"]["key"] in ("slow_motion", "frozen_moment")]
    doc = {"tool": "shot-speak", "version": VERSION, "phrase": phrase, "matched": matched, "interpretation": notes,
           **ctx, "options": options}
    vague, reasons = (False, []) if look or techniques else vagueness(phrase)
    if vague:
        doc["vague"] = True
        doc["vague_reasons"] = reasons
        doc["interpretation"] = ["The look is not clear yet. " + " ".join(reasons) + " Find it with the user in rounds of 2 to 4 mock "
                                 "stills that differ in 1 decision, then lock it."] + doc["interpretation"]
    if look:
        doc["look"] = {"id": look_id, "name": look["name"]}
        doc["interpretation"] = [f"The look you named is, in film language: {look['name'].lower()}. " + " ".join(look["makes"])] + notes
    if unknown_reference:
        doc["unknown_reference"] = True
        doc["interpretation"] = ["You named a film, a show or a person that this tool does not know. It did not guess a look. "
                                 "Ask the user 1 question: what should the viewer feel?"] + doc["interpretation"]
    if not matched:
        doc["interpretation"] = (doc["interpretation"][:1] if unknown_reference else []) + ["No known phrase matched. These are 4 general answers. Ask the user what the viewer should feel."]
    if len(slow) > 1:
        doc["note"] = (f"Options {', '.join(slow)} slow time down. In a finished piece, use slow motion for 1 beat only.")
    return doc


def validate_doc(doc, max_images=DEFAULT_MAX_IMAGES, notes=None):
    """Raise Refusal when the option set breaks a rule. Returns the anti-slop advice for each option.

    The structured decisions of each option are the source of truth: the generated prompts are rebuilt from them
    here (see ``set_prompts``). ``notes`` collects a line for each saved prompt that did not match its decisions.
    """
    options = doc.get("options") or []
    is_round = isinstance(doc.get("round"), dict)
    if is_round and not 2 <= len(options) <= 4:
        raise Refusal(f"A round has 2 to 4 mock stills. This one has {len(options)}.")
    if not is_round and not 3 <= len(options) <= 4:
        raise Refusal(f"An option set has 3 or 4 options. This one has {len(options)}.")
    if len(options) > max_images:
        raise Refusal(f"{len(options)} images are above the cap of {max_images}. Remove options or raise --max-images.")
    labels = [o.get("label") for o in options]
    if len(set(labels)) != len(labels):
        raise Refusal("Option labels must be different.")
    if not is_round and len({o.get("pro_term") for o in options}) != len(options):
        raise Refusal("The options must be different techniques, not variants of one idea.")
    if not is_round and sum(1 for o in options if o.get("recommended")) != 1:
        raise Refusal("Mark exactly 1 option as recommended, with a reason.")
    ctx = doc_ctx(doc)
    context = " . ".join(ctx[k] for k in ("phrase", "subject", "action", "setting"))
    findings = {}
    for option in options:
        for field in ("pro_term", "movement", "placement", "lens", "still"):
            if not option.get(field):
                raise Refusal(f"Option {option.get('label')}: '{field}' is missing.")
        for part in ("light", "grade", "speed"):
            if not isinstance(option.get(part), dict) or not option[part].get("prompt"):
                raise Refusal(f"Option {option.get('label')}: '{part}' needs a 'prompt'.")
            option[part].setdefault("key", "custom")
            option[part].setdefault("name", option[part]["key"])
        option["speed"].setdefault("still", "a sharp frame at the peak of the action")
        option.setdefault("snippet", "{subject} {action}; " + option["movement"])
        set_prompts(option, ctx, notes)
        for field in PROMPT_FIELDS:
            problems = lint_prompt(option[field])
            if problems:
                raise Refusal(f"Option {option['label']} {field} {problems[0]}")
        found = anti_slop_check(option, context)
        if found:
            findings[option["label"]] = found
    return findings


# --------------------------------------------------------------------------
# Text diagrams
# --------------------------------------------------------------------------
TOPDOWN = {
    "arc": """\
   TOP VIEW             light, behind the subject
                              |
                              v
                 S ->              S = subject, faces and moves ->
      C1                           C1 = camera start, behind the shoulder
        '.                         C2 = camera at the profile, side-on
          ' .                .C3   C3 = camera end, front three-quarter
             ' - . C2 . - '        The camera stays on this side of S.
                                   It never reaches the front of the face.""",
    "whip": """\
   TOP VIEW
                               C = camera on a fixed spot
        X <~~~~~~~~~ S ->      X = where the pan starts
          \\  whip   /          S = subject, where the pan lands
           \\  pan  /           The blur between X and S can hide a cut.
            \\     /
               C""",
    "zoom": """\
   TOP VIEW
                               C = camera, far away, does not travel
        S ->  <========  C     ===== the lens zooms; nothing slides
                               S = subject, three-quarter or side-on""",
    "push": """\
   TOP VIEW
                               C = camera start
            S ->               c = camera end
              ^                The camera itself travels toward S
               \\               from a three-quarter side position.
                c              The background slides past.
                 \\
                  C""",
    "pull": """\
   TOP VIEW
                               S = subject, faces ->
            S ->               c = camera start, close, three-quarter behind
           /                   C = camera end, far
          c                    The camera travels away in a straight line.
         /                     S gets small. The place gets large.
        v
       C""",
    "track": """\
   TOP VIEW
                               S = subject, moving ->
        S -> -> -> -> S'       C = camera, travelling parallel
        |  |  |  |  |          | = foreground posts or shapes that wipe past
        C -> -> -> -> C'       One screen direction for the whole shot.""",
    "follow": """\
   TOP VIEW
                               S = subject, moving ->
        C -> S -> -> ->        C = camera, 1 m behind one shoulder
                               The camera stays behind for the whole shot.""",
    "static": """\
   TOP VIEW                 light
                              |
                              v
            S ->               S = subject, side-on to the camera
                               C = camera, locked, low or close
            ^                  The camera looks toward the light.
            |
            C""",
    "static_side": """\
   TOP VIEW
                       light ->
        C --------> S ^        C = camera, locked, exactly side-on, far away
                      |        S = subject, faces up the page (profile to C)
                               The camera is never in front of the face.""",
    "overhead": """\
   SIDE VIEW
            C                  C = camera, 5 m up, pointed straight down
            |                  S = subject
            v                  No horizon in the frame.
        ----S----  floor""",
    "crane": """\
   SIDE VIEW
            C'  (end, 4 m up)
            ^                  C = camera start, low, behind a foreground object
            |                  S = subject, back to the camera
        #   C        S ->      # = foreground object
        -------------------    The rise reveals the place beyond S.""",
    "montage": """\
   TOP VIEW
        C4 (overhead)
                               S = subject
            S ->               C1 floor-level wide   C2 long-lens profile
                               C3 close detail       C4 overhead
      C1   C2   C3             Every camera is on the same side of S.
      -- action line: the cameras never cross it --""",
}

FRAMES = {
    "profile_wide": ["                              ", "        o>     o>             ", "       /|     /|        *sun  ", "       / \\    / \\             ", "______________________________"],
    "three_quarter_back": ["= = = = = = = = = = = = = = = ", "= = =      (o)        = = = = ", "= = =      /|\\        = = = = ", "= = =      / \\        = = = = ", "______________________________"],
    "side_third": ["- - - - - - - - - - - - - - - ", "- - - - - - - -      o>       ", "- - - - - - - -     /|        ", "- - - - - - - -     / \\       ", "______________________________"],
    "tight_three_quarter": ["#                             ", "##          .---.             ", "##         /  o> |            ", "#          \\    /             ", "#        ___|  |___           "],
    "low_wide": ["                    *sun      ", "            o>                ", "           /|\\                ", "  _________/_\\_____________   ", " /  /   /   /   \\   \\   \\   \\ "],
    "profile_cu": ["                              ", "        .-----.      ~  ~  ~  ", "       /   ==o >   ~  ~  ~  ~ ", "       \\      /      ~  ~  ~  ", "     ___|    |____            "],
    "side_full": ["- - - - - - - - - - - - - - - ", "- - - - -    \\o/    - - - - - ", "- - - - -     |>    - - - - - ", "- - - - -    / \\    - - - - - ", "______________________________"],
    "over_shoulder": ["####                          ", "######        .  door  .      ", "#(o)###       |        |      ", "########      |        |      ", "#########_____|________|______"],
    "overhead": ["                              ", "       \\                      ", "        \\  (o)                ", "         \\ long shadow        ", "                              "],
    "back_small": ["     .   wide open place   .  ", "   .                         .", "                              ", "            (o)               ", "____________/|\\_______________"],
    "wide_offcentre": ["####                          ", "####                          ", "####              o>          ", "####             /|\\          ", "####_____________/_\\__________"],
    "foreground_soft": ["((( )))                       ", "(( soft ))        .---.       ", "(( near ))       /  o> |      ", "(( object))      \\    /       ", "((( )))        ___|  |___     "],
    "canted": ["  /        /          /       ", " /        /   o>     /        ", "/        /   /|     /         ", "        /    / \\   /          ", "_ _ - - ~ ~ ^ ^ ` ` ' '       "],
    "silhouette": ["##########          ##########", "##########    @>    ##########", "##########   /#\\    ##########", "##########   / \\    ##########", "##########__________##########"],
    "pov": ["                              ", "        .   place ahead   .   ", "                              ", "    \\                    /    ", "     \\ hands        hands /   "],
    "insert": ["##############################", "####   .-~~~~~~~-.        ####", "###   (  detail   ) <- light ##", "####   `-.......-'        ####", "##############################"],
}


def diagram(option):
    top = TOPDOWN.get(option.get("topdown"), TOPDOWN["static"])
    rows = FRAMES.get(option.get("frame"), FRAMES["side_third"])
    frame = ["   FRAME SKETCH", "   +" + "-" * 30 + "+"] + ["   |" + r.ljust(30)[:30] + "|" for r in rows] + ["   +" + "-" * 30 + "+"]
    return top + "\n\n" + "\n".join(frame)


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------
def render_option(option, image_path=None):
    lines = [f"## Option {option['label']}: {option['pro_term']}" + ("  (recommended)" if option.get("recommended") else ""), ""]
    if option.get("recommended"):
        lines += [f"**Why recommended:** {option.get('recommended_because', '')}", ""]
    if image_path:
        lines += [f"![Option {option['label']}]({image_path})", ""]
    lines += [
        f"**In plain words:** {option.get('plain', '')}",
        f"**What the viewer feels:** {option.get('feel', '')}",
        f"**Pro term to learn:** {option['pro_term']}",
        f"**Choose it when:** {option.get('when', '')}",
    ] + (["", f"**What makes that look ({option['look_name'].lower()}):**"] + [f"- {m}" for m in option["look_makes"]]
         if option.get("look_makes") else []) + [
        "",
        "| Decision | This option |",
        "|---|---|",
        f"| Camera movement | {option['movement']} |",
        f"| Camera placement | {option['placement']} |",
        f"| Lens | {option['lens']}. {option.get('lens_why', '')} |",
        f"| Light | {option['light']['name']}: {option['light'].get('plain', '')} |",
        f"| Colour grade | {option['grade']['name']}: {option['grade'].get('plain', '')} |",
        f"| Speed | {option['speed']['name']}: {option['speed'].get('plain', '')} |",
        f"| Length | {option.get('duration', '')} |",
        "",
        "**AI look it avoids:** " + "; ".join(option.get("slop_avoided", [])) + ".",
        "",
        "**Risks with AI video generators:**",
    ] + [f"- {risk}" for risk in option.get("risks", [])] + [
        "",
        "**Say this to a video model:**",
        "",
        "```text", option["video_snippet"], "```",
        "",
        "**Framing diagram:**",
        "",
        "```text", diagram(option), "```",
        "",
        "**Mock image prompt (paste into any image tool):**",
        "",
        "```text", option["image_prompt"], "```",
        "",
    ]
    return "\n".join(lines)


def render_markdown(doc, images=None):
    images = images or {}
    head = [f"# Shot options for: \"{doc['phrase']}\"", ""]
    if doc.get("interpretation"):
        head += ["**What your words mean in film language:**", ""] + [f"- {n}" for n in doc["interpretation"]] + [""]
    head += [f"Subject: {doc['subject']} {doc['action']}. Place: {doc['setting']}. Frame: {doc['aspect']}.", ""]
    if doc.get("note"):
        head += [f"Note: {doc['note']}", ""]
    body = [render_option(o, images.get(o["label"])) for o in doc["options"]]
    tail = ["---", "", "Pick 1 option, mix parts of 2 options (for example \"A with the light of C\"), or ask for other options.", ""]
    return "\n".join(head + body + tail)


def write_json(path, data, ensure_ascii=False):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=ensure_ascii) + "\n", encoding="utf-8")


def write_outputs(doc, out_dir, images=None):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "options.json", doc)
    (out / "options.md").write_text(render_markdown(doc, images), encoding="utf-8")
    return out


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "shot"


# --------------------------------------------------------------------------
# Cost
# --------------------------------------------------------------------------
def estimate(backend, count, env):
    """Return (total USD or None, basis text)."""
    name = backend["name"]
    if name in ("text", "host"):
        return 0.0, "No paid API request from this tool."
    override = env_value(env, "SHOTSPEAK_EST_USD_PER_IMAGE")
    if override:
        try:
            per = float(override)
        except ValueError:
            raise Refusal("SHOTSPEAK_EST_USD_PER_IMAGE must be a number.")
        return round(per * count, 4), f"{count} x {per:g} USD from SHOTSPEAK_EST_USD_PER_IMAGE. Planning estimate, not a provider quote."
    if name == "openai" and backend["model"] == OPENAI_DEFAULT_MODEL:
        per = OPENAI_EST_USD_PER_IMAGE
        return round(per * count, 4), (f"{count} x {per:g} USD. Planning estimate for the default model, not a provider quote. "
                                       "The provider bills by tokens; check the final charge at the provider.")
    return None, ("Unknown for this model. Read the provider's price page, then set SHOTSPEAK_EST_USD_PER_IMAGE, "
                  "or add --accept-unknown-cost after the user accepted an unknown cost.")


def request_fingerprint(backend, size, quality, prompts, env):
    """The card fingerprint. It binds the approval to everything that decides the requests and their cost:
    the backend, the model, the size, the quality, every prompt, the extra input fields, and the estimate that the
    card shows (the number of images and the total). A changed request or a changed estimate needs a new yes.
    """
    prompts = list(prompts)
    total, _basis = estimate(backend, len(prompts), env)
    extra = provider_extra(env, backend["name"])
    payload = [backend["name"], backend["model"], size, quality, prompts, {"images": len(prompts), "estimated_total_usd": total}]
    return hashlib.sha256(json.dumps(payload + ([extra] if extra else []), sort_keys=True).encode("utf-8")).hexdigest()[:12]


def card(doc, backend, size, quality, env):
    total, basis = estimate(backend, len(doc["options"]), env)
    prompts = [o["image_prompt"] for o in doc["options"]]
    return {"backend": backend["name"], "model": backend["model"], "size": size, "quality": quality,
            "images": len(prompts), "estimated_total_usd": total, "basis": basis,
            "fingerprint": request_fingerprint(backend, size, quality, prompts, env)}


def print_card(doc, info, out_dir, stream=None):
    stream = stream or sys.stdout

    def w(line=""):
        print(line, file=stream)

    w(f"SHOT-SPEAK MOCK CARD  \"{doc['phrase']}\"")
    for option in doc["options"]:
        w()
        w(f"--- Option {option['label']}: {option['pro_term']}" + ("  [recommended]" if option.get("recommended") else ""))
        w(option["image_prompt"])
        w(f"-> {Path(out_dir) / ('option_' + option['label'] + '.png')}")
    w()
    w(f"Backend:   {info['backend']}" + (f"  (model {info['model']})" if info["model"] else ""))
    if info["backend"] not in ("text", "host"):
        w(f"Size:      {info['size']}   Quality: {info['quality']}")
    w(f"Images:    {info['images']}")
    cost = "unknown" if info["estimated_total_usd"] is None else f"{info['estimated_total_usd']:.2f} USD"
    w(f"Estimate:  {cost}")
    w(f"Basis:     {info['basis']}")
    w(f"Card:      {info['fingerprint']}")
    if info.get("key_missing"):
        w(f"Key:       {info['key_missing']} was not found. A live run needs it in the environment or in .env.local.")


# --------------------------------------------------------------------------
# Providers. One request for each image. No automatic retry.
# --------------------------------------------------------------------------
class ProviderError(Exception):
    def __init__(self, message, ambiguous):
        super().__init__(message)
        self.ambiguous = ambiguous


# A provider answer larger than this is refused. A mock still is a few MB; base64 makes it a third larger.
MAX_ANSWER_BYTES = 50_000_000


# Headers that carry an account credential. They go only to the host that the request was made for.
_CREDENTIAL_HEADERS = {"authorization", "proxy-authorization", "cookie", "x-api-key"}


class _RedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only to an https address. A redirect to another host gets no credential header."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urlsplit(newurl)
        if target.scheme != "https":
            raise ProviderError("The provider sent a redirect to an address that is not https. It was not followed.", ambiguous=True)
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and target.hostname != urllib.parse.urlsplit(req.full_url).hostname:
            for name in [h for h in new.headers if h.lower() in _CREDENTIAL_HEADERS]:
                del new.headers[name]
        return new


@functools.lru_cache(maxsize=1)
def _opener():
    return urllib.request.build_opener(_RedirectHandler)


def http_transport(method, url, headers, body=None, timeout=180):
    """Return (status, bytes). Raises ProviderError. Tests replace this function."""
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with _opener().open(request, timeout=timeout) as response:
            data = response.read(MAX_ANSWER_BYTES + 1)
            if len(data) > MAX_ANSWER_BYTES:
                raise ProviderError(f"The answer is larger than {MAX_ANSWER_BYTES // 1_000_000} MB. It was not used.", ambiguous=True)
            return response.status, data
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:400].decode("utf-8", "replace")
        raise ProviderError(f"HTTP {exc.code}: {detail}", ambiguous=exc.code >= 500)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ProviderError(f"No answer from the provider: {exc}", ambiguous=True)
    except http.client.HTTPException as exc:  # for example an answer that stops before its end
        raise ProviderError(f"The answer was cut off ({type(exc).__name__}).", ambiguous=True)


def _json_call(transport, method, url, headers, payload=None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    status, raw = transport(method, url, {**headers, "Content-Type": "application/json"}, body)
    try:
        return json.loads(raw.decode("utf-8"))
    except ValueError:
        raise ProviderError(f"HTTP {status}: the answer is not JSON.", ambiguous=True)


def image_suffix(data):
    """'.png', '.jpg' or '.webp' for the bytes of 1 complete image. None for anything else, or a cut-off file."""
    if not data or len(data) > MAX_ANSWER_BYTES:
        return None
    if data[:8] == b"\x89PNG\r\n\x1a\n" and data[-12:-8] == b"\x00\x00\x00\x00" and data[-8:-4] == b"IEND":
        return ".png"
    if data[:3] == b"\xff\xd8\xff" and data.rstrip(b"\x00")[-2:] == b"\xff\xd9":
        return ".jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP" and int.from_bytes(data[4:8], "little") + 8 in (len(data), len(data) - 1):
        return ".webp"
    return None


def checked_image(data):
    """The image bytes of a provider answer, or ProviderError. The request was sent, so a bad answer is ambiguous."""
    if not image_suffix(data):
        raise ProviderError(f"The provider answered with {len(data or b'')} bytes that are not 1 complete PNG, JPEG or WebP image. "
                            "Nothing was saved.", ambiguous=True)
    return data


def _fetch(transport, url):
    """The bytes of the image link in a provider answer. Only an https link is opened; a data: image is decoded here."""
    if isinstance(url, str) and re.match(r"data:image/[a-z]+;base64,", url):
        try:
            return base64.b64decode(url.split(",", 1)[1], validate=True)
        except ValueError:
            raise ProviderError("The provider's data: image is not valid base64.", ambiguous=True)
    if not (isinstance(url, str) and url.startswith("https://")):
        raise ProviderError("The provider's image link is not an https link. It was not opened.", ambiguous=True)
    return transport("GET", url, {})[1]


def _first_url(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list) and value:
        return _first_url(value[0])
    if isinstance(value, dict):
        return value.get("url")
    return None


EXTRA_INPUT_VARS = {"fal": "SHOTSPEAK_FAL_EXTRA_INPUT", "replicate": "SHOTSPEAK_REPLICATE_EXTRA_INPUT",
                    "higgsfield": "SHOTSPEAK_HIGGSFIELD_EXTRA_INPUT"}
# Fields that only the tool sets: the prompt, and the number of images (the cost cap counts 1 image for each request).
RESERVED_INPUTS = {"prompt", "n", "num_images", "num_outputs", "batch_size", "count", "samples", "num_samples"}
_MODEL_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._:-]*)*")


def _strings(value, path=""):
    """(path, text) for every key and every string value in a JSON value."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield f"{path}{key}", str(key)
            yield from _strings(item, f"{path}{key}.")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _strings(item, f"{path}{index}.")
    elif isinstance(value, str):
        yield path.rstrip("."), value


def provider_extra(env, name):
    """The extra input fields for a provider, from its SHOTSPEAK_<NAME>_EXTRA_INPUT variable. {} when there are none.

    Refused: a field that the tool sets itself (the prompt, the image count), and any key or value that holds a link,
    a file path, an email address, a key or a protected name. No user image or personal data goes out this way.
    """
    var = EXTRA_INPUT_VARS.get(name)
    raw = env_value(env, var) if var else None
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except ValueError:
        value = None
    if not isinstance(value, dict):
        raise Refusal(f"{var} must be a JSON object.")
    reserved = sorted(RESERVED_INPUTS & {str(k).lower() for k in value})
    if reserved:
        raise Refusal(f"{var} cannot set {', '.join(reserved)}: the tool sets the prompt and asks for 1 image in each request.")
    for where, text in _strings(value):
        if private_data(text) or banned_names(text):
            raise Refusal(f"{var}: '{where}' holds a link, a file path, an email address, a key or a protected name. Nothing was sent.")
    return value


PROVIDER_URLS = {"openai": lambda model: OPENAI_URL, "fal": lambda model: "https://fal.run/" + model,
                 "replicate": lambda model: f"https://api.replicate.com/v1/models/{model}/predictions",
                 "higgsfield": lambda model: f"{HIGGSFIELD_API}/{model}"}


def request_for(backend, prompt, size, quality, env):
    """(URL, JSON body) of the 1 request that makes 1 image. With the key header, this is all that leaves the machine."""
    name, model = backend["name"], backend["model"]
    if name not in PROVIDER_URLS:
        raise Refusal(f"Backend '{name}' sends no request.")
    if not model or not _MODEL_ID_RE.fullmatch(model) or ".." in model:
        raise Refusal(f"'{model}' is not a model id that this tool sends to {name}.")
    problems = lint_prompt(prompt)
    if problems:
        raise Refusal("The image prompt " + problems[0])
    extra = provider_extra(env, name)
    if name == "openai":
        body = {"model": model, "prompt": prompt, "size": size, "quality": quality, "n": 1}
    elif name == "replicate":
        body = {"input": {**extra, "prompt": prompt}}
    else:
        body = {**extra, "prompt": prompt}
    return PROVIDER_URLS[name](model), body


def gen_openai(prompt, backend, key, size, quality, env, transport):
    url, body = request_for({**backend, "name": "openai"}, prompt, size, quality, env)
    data = _json_call(transport, "POST", url, {"Authorization": f"Bearer {key}"}, body)
    item = (data.get("data") or [{}])[0]
    if item.get("b64_json"):
        try:
            image = base64.b64decode(item["b64_json"], validate=True)
        except ValueError:
            raise ProviderError("The provider's image is not valid base64.", ambiguous=True)
    else:
        image = _fetch(transport, item["url"]) if item.get("url") else None
    if not image:
        raise ProviderError("The provider answered without an image.", ambiguous=True)
    usage = data.get("usage") or {}
    details = usage.get("input_tokens_details") or {}
    measured = None
    if all(isinstance(v, int) for v in (details.get("text_tokens"), details.get("image_tokens"), usage.get("output_tokens"))):
        measured = round((details["text_tokens"] * OPENAI_RATES["text_input"] + details["image_tokens"] * OPENAI_RATES["image_input"]
                          + usage["output_tokens"] * OPENAI_RATES["image_output"]) / 1_000_000, 6)
    return checked_image(image), {"usage": usage, "measured_usd_at_published_rates": measured}


def gen_fal(prompt, backend, key, size, quality, env, transport):
    url, body = request_for({**backend, "name": "fal"}, prompt, size, quality, env)
    data = _json_call(transport, "POST", url, {"Authorization": f"Key {key}"}, body)
    link = _first_url(data.get("images") or data.get("image"))
    if not link:
        raise ProviderError("The provider answered without an image URL.", ambiguous=True)
    return checked_image(_fetch(transport, link)), {"request_id": data.get("request_id")}


def gen_replicate(prompt, backend, key, size, quality, env, transport, poll_seconds=2, max_polls=60, max_seconds=300,
                  sleep=time.sleep, clock=time.monotonic):
    """Create 1 prediction, then check its status link. The key goes only to the https host of the create request.
    The checks stop after ``max_polls`` or ``max_seconds``. The prediction is never created again."""
    headers = {"Authorization": f"Bearer {key}", "Prefer": "wait"}
    url, body = request_for({**backend, "name": "replicate"}, prompt, size, quality, env)
    data = _json_call(transport, "POST", url, headers, body)
    host, polls, started = urllib.parse.urlsplit(url).hostname, 0, clock()
    while data.get("status") in ("starting", "processing"):
        if polls >= max_polls or clock() - started >= max_seconds:
            raise ProviderError(f"Prediction {data.get('id')} was still '{data.get('status')}' after {polls} checks in "
                                f"{clock() - started:.0f} s. It was not created again.", ambiguous=True)
        get_url = str((data.get("urls") or {}).get("get") or "")
        link = urllib.parse.urlsplit(get_url)
        if link.scheme != "https" or link.hostname != host:
            raise ProviderError(f"Prediction {data.get('id')}: the status link is not on the https host of the request. "
                                "It was not opened, and the prediction was not created again.", ambiguous=True)
        sleep(poll_seconds)
        data = _json_call(transport, "GET", get_url, {"Authorization": f"Bearer {key}"})
        polls += 1
    if data.get("status") != "succeeded":
        raise ProviderError(f"Prediction {data.get('id')} ended with status '{data.get('status')}': {data.get('error')}",
                            ambiguous=False)
    link = _first_url(data.get("output"))
    if not link:
        raise ProviderError("The provider answered without an image URL.", ambiguous=True)
    return checked_image(_fetch(transport, link)), {"prediction_id": data.get("id")}


def _find_url(value):
    """The first https link in a provider answer, wherever it is."""
    if isinstance(value, str):
        return value if value.startswith("https://") else None
    if isinstance(value, dict):
        for key in ("images", "image", "url", "result", "output", "results"):
            if key in value:
                found = _find_url(value[key])
                if found:
                    return found
        value = [v for k, v in value.items() if k != "status_url"]
    if isinstance(value, list):
        for item in value:
            found = _find_url(item)
            if found:
                return found
    return None


def gen_higgsfield(prompt, backend, key, size, quality, env, transport, poll_seconds=3, max_polls=60, sleep=time.sleep):
    """Submit, then poll the status link of that request. One submit. The submit is never sent again."""
    headers = {"Authorization": f"Key {key}"}
    url, body = request_for({**backend, "name": "higgsfield"}, prompt, size, quality, env)
    data = _json_call(transport, "POST", url, headers, body)
    request_id, status_url = data.get("request_id"), data.get("status_url")
    polls = 0
    while str(data.get("status", "")).lower() in ("queued", "in_progress") and polls < max_polls:
        if not status_url or not str(status_url).startswith(HIGGSFIELD_API + "/requests/"):
            break
        sleep(poll_seconds)
        data = _json_call(transport, "GET", status_url, headers)
        polls += 1
    status = str(data.get("status", "")).lower()
    if status != "completed":
        raise ProviderError(f"Request {request_id} ended with status '{status or 'unknown'}'.",
                            ambiguous=status in ("queued", "in_progress", ""))
    link = _find_url(data)
    if not link:
        raise ProviderError("The provider answered without an image link.", ambiguous=True)
    return checked_image(_fetch(transport, link)), {"request_id": request_id}


GENERATORS = {"higgsfield": gen_higgsfield, "openai": gen_openai, "fal": gen_fal, "replicate": gen_replicate}


def validate_size(size):
    match = re.fullmatch(r"(\d+)x(\d+)", size)
    if not match:
        raise Refusal("--size must be WIDTHxHEIGHT, for example 1536x864.")
    width, height = int(match.group(1)), int(match.group(2))
    if width % 16 or height % 16 or max(width, height) > 3840 or max(width, height) / min(width, height) > 3 \
            or not 655_360 <= width * height <= 8_294_400:
        raise Refusal("--size: use multiples of 16, a long edge of 3840 or less, a ratio of 3:1 or less, "
                      "and 655,360 to 8,294,400 pixels in total.")


IMAGE_SUFFIXES = (".png", ".jpg", ".webp")
DONE = ("ok", "reused", "imported")  # receipt statuses with an image on disk


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def load_receipts(out):
    """{option label: its latest receipt} from receipts.json. An unreadable file gives {}."""
    try:
        receipts = json.loads((Path(out) / "receipts.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(receipts, list):
        return {}
    return {r["option"]: r for r in receipts if isinstance(r, dict) and r.get("option")}


def atomic_write(path, data):
    """Write the whole file or nothing: a stopped run never leaves half a file under the real name."""
    path = Path(path)
    part = path.with_name(path.name + ".part")
    part.write_bytes(data)
    os.replace(part, path)


def save_receipts(out, book):
    atomic_write(Path(out) / "receipts.json", (json.dumps([book[k] for k in sorted(book)], indent=2) + "\n").encode("utf-8"))


def reusable(out, label, receipt, request_sha256, prompt_sha256):
    """The receipt of an image that this exact request already made (or that the user imported for this exact prompt),
    when its file is still there with the same bytes. Else None: a missing or different receipt is never a cache hit."""
    if not receipt or receipt.get("status") not in DONE:
        return None
    if receipt["status"] == "imported":
        if receipt.get("prompt_sha256") != prompt_sha256:
            return None
    elif receipt.get("request_sha256") != request_sha256:
        return None
    name = str(receipt.get("file", ""))
    if not re.fullmatch(rf"option_{re.escape(label)}\.(png|jpg|webp)", name):
        return None
    try:
        data = (Path(out) / name).read_bytes()
    except OSError:
        return None
    return receipt if _sha256(data) == receipt.get("image_sha256") and image_suffix(data) else None


def generate(doc, backend, env, out_dir, size, quality, transport=None, force=False, log=None):
    """Send 1 request for each option that has no image for exactly this request yet. Returns this run's receipts.

    An image is reused only when its receipt names the same request (see ``request_for``) and its file still has the
    receipt's hash. ``force`` requests every image again. The run stops at the first failure. A new image is checked,
    then written in 1 step, and replaces the option's older file. ``receipts.json`` keeps the latest receipt of each
    option and is written after each request.
    """
    transport = transport or http_transport
    log = log or (lambda s: print(s, file=sys.stderr))
    secrets = secrets_of(env)
    key = env[backend["key_var"]][0]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    book, receipts, images = load_receipts(out), [], {}
    for option in doc["options"]:
        label, prompt = option["label"], option["image_prompt"]
        url, body = request_for(backend, prompt, size, quality, env)
        base = {"option": label, "backend": backend["name"], "model": backend["model"],
                "prompt_sha256": _sha256(prompt.encode("utf-8")),
                "request_sha256": _sha256(json.dumps({"url": url, "body": body}, sort_keys=True).encode("utf-8"))}
        hit = None if force else reusable(out, label, book.get(label), base["request_sha256"], base["prompt_sha256"])
        if hit:
            receipt = hit if hit["status"] == "imported" else {**base, "status": "reused", "file": hit["file"],
                                                               "image_sha256": hit["image_sha256"]}
            log(f"Option {label}: {hit['file']} was made for this exact request. Not requested again.")
        else:
            started = time.time()
            try:
                image, extra = GENERATORS[backend["name"]](prompt, backend, key, size, quality, env, transport)
            except ProviderError as exc:
                status = "ambiguous" if exc.ambiguous else "rejected"
                book[label] = {**base, "status": status, "error": redact(exc, secrets)}
                receipts.append(book[label])
                save_receipts(out, book)
                log(redact(f"Option {label}: {status}. {exc}", secrets))
                if exc.ambiguous:
                    log("The result of this request is unknown. It was NOT sent again. Check the provider's usage page before a new request.")
                log("Stopped. The options after this one were not requested.")
                break
            suffix = image_suffix(image)
            target = out / f"option_{label}{suffix}"
            atomic_write(target, image)
            for old in out.glob(f"option_{label}.*"):
                if old.suffix in IMAGE_SUFFIXES and old != target:
                    old.unlink()
                    log(f"Option {label}: removed {old.name}, the image of an older request.")
            receipt = {**base, "status": "ok", "file": target.name, "format": suffix[1:], "bytes": len(image),
                       "seconds": round(time.time() - started, 1), "image_sha256": _sha256(image), **extra}
            log(f"Option {label}: saved {target}")
        book[label] = receipt
        receipts.append(receipt)
        images[label] = receipt["file"]
        save_receipts(out, book)
    write_outputs(doc, out, images)
    return receipts


# --------------------------------------------------------------------------
# De-slop mode
# --------------------------------------------------------------------------
# Each rewrite belongs to 1 tell. It runs only on the parts of the prompt that ask for something, only when its tell
# was flagged there, and never on evidence that the user intends (see ``scan``).
REWRITES = [
    ("hdr_saturated", r",?\s*\b(8k|4k|hdr|ultra[- ]?(realistic|detailed|hd)|hyper[- ]?real(istic)?|highly detailed|masterpiece|award[- ]winning|stunning|breathtaking|trending[^,.]*|unreal engine|octane render|vibrant colou?rs|vivid colou?rs)\b", ""),
    ("soft_glow", r",?\s*\b(beautiful lighting|perfect lighting)\b", ""),
    ("slowmo_everywhere", r"\b(epic |dramatic |super )?slow[- ]?mo(tion)? (throughout|everywhere)\b|\b(all|everything) in slow[- ]?motion\b", "real time, with one short slow-motion beat at the peak of the action", "real time"),
    ("eyes_to_lens", r"\b(look(s|ing)?|stares?|staring|smil(es|ing)) (straight |directly |right )?(at|into|to) (the )?(camera|lens|viewer)\b", "with the eyes on a target inside the scene, off the lens"),
    ("frontal_centred", r"\b(front[- ]?facing|facing (the )?(camera|viewer|lens)|straight[- ]on|head[- ]on)\b", "seen from a three-quarter side position"),
    ("frontal_centred", r"\b((?<!off-)(centered|centred)|in the (center|centre) of (the )?frame)\b", "off-centre, on one third of the frame"),
    ("orbit_full", r"\b(360|three[- ]sixty|full|180)[- ]?(degree|deg|°)? ?(orbit|circle|rotation)\b", "partial arc of about 130 degrees"),
    ("orbit_full", r"\b(the )?(camera )?slowly (orbiting|circling|spinning|rotating) around\b", "the camera, in one fast move, arcs about 130 degrees around, never to the front of,"),
    ("orbit_full", r"\b(orbit(s|ing)?|circl(es?|ing)|spin(s|ning)?) (all the way )?around\b", "arcs about 130 degrees around, never to the front of,"),
    ("aquarium_speed", r"\b(a |the )?slow(ly)? (floating|drifting|gliding) (camera|shot)\b|\b(a |the )?floating camera\b", "the camera, in one fast decisive move,"),
    ("aquarium_speed", r"\bcamera (floats|drifts|glides)\b|\bsmooth cinematic (movement|motion|camera)\b|\bgentle camera movement\b", "one decisive camera move with a clear start and end"),
    ("soft_glow", r"\b(soft (golden |warm |even )?glow|golden glow|warm glow|ethereal glow|evenly lit|well[- ]lit)\b", "one hard light source from one side, with a real dark side"),
    ("bloom_haze", r",?\s*\b(with |and )?(bloom|haze|hazy atmosphere|mist|fog|god[- ]?rays?|volumetric (light|lighting|rays|fog)|light shafts?|atmospheric (haze|fog|smoke))\b", ""),
    ("flare_spam", r",?\s*\b(with |and )?(lens flares?|anamorphic flares?|light leaks?)\b", ""),
    ("glossy_floor", r"\b(wet|glossy|reflective|rain[- ]slick(ed)?) (floor|street|streets|ground|pavement|asphalt|surface)\b", r"matte, worn \3"),
    ("fake_bokeh", r"\b(creamy|beautiful|heavy) bokeh\b|\bbokeh background\b|\b(blurred|blurry) background\b", "the background soft with natural falloff from a long lens"),
    ("teal_orange_default", r"\b(teal and orange|orange and teal|teal[- ]orange)( colou?r)?( grad(e|ing))?\b|\bcinematic colou?r grad(e|ing)\b", "a film-print grade with deep true blacks and restrained colour"),
    ("floating_bodies", r"\b(float(s|ing)?|hover(s|ing)?|glid(es|ing)|fl(ies|ying)) (in|through) (the )?air\b", "jumps to a real, modest height with real gravity"),
    ("perfect_textures", r"\b(flawless|pristine|spotless|immaculate|polished|sleek)\b", "worn"),
    ("vague_cinematic", r",?\s*\b(cinematic|epic|movie[- ]like|film[- ]like|professional)\b", ""),
]
# A tell that a rewrite only deletes leaves no decision behind, so its avoid clause is added. A missing decision
# lets the generator fall into 1 default: its fill line asks for the decision and the matching clause guards it.
REMOVED_ONLY = ("hdr_saturated", "bloom_haze", "flare_spam")
MISSING_GUARD = {"missing_camera": "eyes_to_lens", "missing_light": "soft_glow", "missing_speed": "aquarium_speed"}

MISSING_FILL = {
    "missing_camera": "Camera: [state the height, the side and the distance, for example 'low at knee height, side-on, 3 m away'].",
    "missing_lens": "Lens: [state a focal length for a feeling, for example '18 mm on the floor' or '85 mm from far away'].",
    "missing_light": "Light: [name one source and its direction, for example 'one hard low sun behind the subject'; about a third of the frame in true shadow].",
    "missing_speed": "Speed: [state 'real time', or the one beat that is slow].",
}


def deslop(text, context=""):
    """Return (flagged tells, rewritten text). The rewrite is a starting point for the agent.

    Proportional: a prompt with no flagged tell comes back unchanged. Only the parts that ask for a flagged tell
    are rewritten; "no fog" and a technique that the user intends stay as written. Running deslop on its own
    rewrite changes nothing more. The kept tells are in ``scan(text, True, context)[1]``.
    """
    tells, _kept = scan(text, check_missing=True, context=context)
    if not tells:
        return tells, text
    flagged = {t["id"] for t in tells}
    forbidden = {t["id"] for t in tells if t.get("contradiction")}
    intent = {t: bool(C.SLOP_BY_ID[t].get("intent") and re.search(C.SLOP_BY_ID[t]["intent"], f"{text} . {context}", re.I)) for t in flagged}

    def rewrite(part, purpose):
        for tell_id, pattern, replacement, *if_forbidden in REWRITES:
            tell = C.SLOP_BY_ID[tell_id]
            if if_forbidden and tell_id in forbidden:  # the prompt forbids it elsewhere: do not bring it back
                replacement = if_forbidden[0]
            if tell_id not in flagged or (tell.get("needs") and not re.search(tell["needs"], part, re.I)):
                continue
            part = re.sub(pattern, lambda m, t=tell, r=replacement: m.group(0) if _spared(t, m.group(0), intent[t["id"]] or purpose)
                          else m.expand(r), part, flags=re.I)
        return part

    rewritten = "".join(rewrite(part, purpose) if kind == "ask" else part for part, kind, purpose in segments(text))
    rewritten = re.sub(r"\s+,", ",", re.sub(r"[ \t]{2,}", " ", rewritten))
    rewritten = re.sub(r",\s*(?=[.,;])|^\s*,\s*", "", rewritten).strip().rstrip(",")
    rewritten = re.sub(r"([.;!?])(?:\s*[.;])+(?=\s|$)", r"\1", rewritten)  # a removed last clause leaves no ". ."
    if rewritten and rewritten[-1] not in ".!?":
        rewritten += "."
    rewritten = rewritten[:1].upper() + rewritten[1:]
    additions = [MISSING_FILL[t["id"]] for t in tells if t["id"] in MISSING_FILL]
    guards = [t for t in REMOVED_ONLY if t in flagged] + [MISSING_GUARD[t] for t in MISSING_GUARD if t in flagged]
    guards = [g for g in avoid_clauses(guards) if g not in rewritten]
    return tells, " ".join([rewritten] + additions + (["Avoid: " + "; ".join(guards) + "."] if guards else []))


# --------------------------------------------------------------------------
# Choose / mix
# --------------------------------------------------------------------------
MIX_PARTS = ("lens", "light", "grade", "speed")
LAYOUT_LINE = ("LAYOUT REFERENCE: the attached grey-box frame gives the camera position, the framing and where each person "
               "stands. Take nothing else from it: no grey surfaces, no checker floor, no mannequin shapes, no colours, no light.")


def previs_for(manifest, label):
    """The previs files of 1 option, or None. ``manifest`` is the content of previs.json."""
    for entry in (manifest or {}).get("options", []):
        if entry.get("label") == label and entry.get("status") == "ok":
            return {"label": label, "files": {f["role"]: f["path"] for f in entry["files"]}, "summary": entry["summary"],
                    "notes": entry.get("notes", []) + entry.get("hidden", [])}
    return None


def choose(doc, pick, mix=None, action_text=None, previs=None, layout_ref=False):
    by_label = {o["label"]: o for o in doc["options"]}
    if pick not in by_label:
        raise Refusal(f"No option '{pick}'. Options: {', '.join(by_label)}.")
    final = copy.deepcopy(by_label[pick])
    mixed = {}
    for item in mix or []:
        if "=" not in item:
            raise Refusal("Write each mix as PART=LABEL, for example light=C.")
        part, label = item.split("=", 1)
        if part not in MIX_PARTS or label not in by_label:
            raise Refusal(f"Mix '{item}': the part must be one of {', '.join(MIX_PARTS)} and the label one of {', '.join(by_label)}.")
        final[part] = copy.deepcopy(by_label[label][part])
        if part == "lens":
            final["lens_why"] = by_label[label].get("lens_why", "")
        mixed[part] = label
    ctx = doc_ctx(doc, action_text)
    # The prompts follow the final decisions. A hand-edited prompt of the picked option is kept when nothing changed it.
    notes, picked = [], by_label[pick]
    for field, build in (("image_prompt", build_image_prompt), ("video_snippet", build_video_snippet)):
        if is_custom(picked, field) and not mixed and not action_text:
            final[field] = picked[field]
        else:
            if is_custom(picked, field):
                notes.append(f"Your own {field} of option {pick} was not used: the mix or the new action changes its decisions.")
            final[field] = build(final, ctx)
    image_prompt = final.pop("image_prompt")  # the mock still of the final mix
    findings = anti_slop_check(final, " . ".join(ctx[k] for k in ("phrase", "subject", "action", "setting")))
    tells = list(C.TECHNIQUES.get(final.get("technique"), {}).get("slop_avoids", [])) + C.VIDEO_BASE_AVOID + ["soft_glow", "perfect_textures"]
    if not _airborne(final, ctx):
        tells = [t for t in tells if t != "floating_bodies"]
    if final["light"]["key"] in ("overcast_soft", "high_key"):
        tells = [t for t in tells if t != "soft_glow"]
    block = [
        f"SHOT: {final['pro_term']}. {ctx['aspect']} frame, {final.get('duration', '3 to 5 s')}.",
        f"SUBJECT AND ACTION: {ctx['subject']} {ctx['action']}, in {ctx['setting']}.",
        f"CAMERA MOVE: {final['movement']}.",
        f"CAMERA PLACEMENT: {final['placement']}.",
        f"LENS: {final['lens']}.",
        f"LIGHT: {final['light']['prompt']}.",
        f"COLOUR: {final['grade']['prompt']}.",
        f"SPEED: {final['speed']['prompt']}.",
    ] + ([f"LOOK: {final['look_clause']}."] if final.get("look_clause") else []) + [
        "RULES: State the exact number of people. Screen direction stays the same for the whole shot.",
        "AVOID: " + "; ".join(avoid_clauses(tells, user_choices(ctx))) + ".",
    ] + ([LAYOUT_LINE] if layout_ref else [])
    block = medium_text("\n".join(block), ctx)
    if layout_ref and not previs:
        raise Refusal("--layout-ref needs a previs for the picked option. Run 'previs' first.")
    if previs and {"lens", "speed"} & set(mixed):
        previs = dict(previs, notes=previs["notes"] + ["The lens or the speed came from another option. Run 'previs' again for an exact frame."])
    problems = lint_prompt(block)
    if problems:
        raise Refusal("The final prompt " + problems[0])
    return {"tool": "shot-speak", "version": VERSION, "phrase": doc["phrase"], "picked": pick, "mixed": mixed,
            "spec": {"pro_term": final["pro_term"], "movement": final["movement"], "placement": final["placement"],
                     "lens": final["lens"], "lens_why": final.get("lens_why", ""), "light": final["light"]["name"],
                     "grade": final["grade"]["name"], "speed": final["speed"]["name"], "duration": final.get("duration", ""),
                     "risks": final.get("risks", [])},
            "anti_slop_findings": findings, "one_line": final["video_snippet"], "prompt_block": block,
            "image_prompt": image_prompt, **({"notes": notes} if notes else {}),
            **({"previs": previs, "layout_reference": bool(layout_ref)} if previs else {})}


def render_choice(choice):
    spec = choice["spec"]
    mixed = ", ".join(f"{part} from {label}" for part, label in choice["mixed"].items()) or "none"
    lines = [f"# Final shot spec: {spec['pro_term']}", "", f"Picked: option {choice['picked']}. Mixed in: {mixed}.", ""]
    if choice.get("lock"):
        lines += [f"**{LOCK_LINES[choice['lock']['status']]}**", ""]
    lines += [
        "| Decision | Final |", "|---|---|",
        f"| Camera movement | {spec['movement']} |", f"| Camera placement | {spec['placement']} |",
        f"| Lens | {spec['lens']}. {spec['lens_why']} |", f"| Light | {spec['light']} |",
        f"| Colour grade | {spec['grade']} |", f"| Speed | {spec['speed']} |", f"| Length | {spec['duration']} |", "",
        "## Watch for", ""] + [f"- {r}" for r in spec["risks"]] + [
        "", "## Prompt block", "", "```text", choice["prompt_block"], "```", "",
        "## One line", "", "```text", choice["one_line"], "```", ""]
    if choice.get("notes"):
        lines += [f"Note: {n}" for n in choice["notes"]] + [""]
    if choice["anti_slop_findings"]:
        lines += ["## Anti-slop advice", ""] + [f"- {f}" for f in choice["anti_slop_findings"]] + [""]
    if choice.get("previs"):
        files = choice["previs"]["files"]
        lines += ["## Blocking previs", "", P.USE_RULE, ""]
        lines += [f"- {role.replace('_', ' ')}: `previs/{path}`" for role, path in files.items()]
        lines += [f"- Note: {note}" for note in choice["previs"]["notes"]]
        lines += ["", "Optional, and free: attach `previs/" + files.get("still_start", "") + "` as a layout reference or a start frame, "
                  "and `previs/" + files.get("still_end", "") + "` as an end frame, when the video tool accepts them.",
                  "Give the reference 1 job in the prompt. Check the generated take for grey surfaces, a checker floor or mannequin shapes.", ""]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _load_doc(args):
    if getattr(args, "options", None):
        try:
            return json.loads(Path(args.options).read_text(encoding="utf-8")), Path(args.options).parent
        except (OSError, ValueError) as exc:
            raise Refusal(f"Cannot read {args.options}: {exc}")
    if not getattr(args, "phrase", None):
        raise Refusal("Give --phrase \"...\" or --options PATH.")
    techniques = [t.strip() for t in args.techniques.split(",")] if getattr(args, "techniques", None) else None
    doc = build_options(args.phrase, args.subject, args.action, args.setting, args.aspect, args.count, techniques)
    return doc, Path(args.out) if args.out else Path("shotspeak_out") / slug(args.phrase)


def cmd_detect(args, env):
    found = detect_backends(env)
    if not found:
        print("No image API key found (looked for OPENAI_API_KEY, HF_KEY, FAL_KEY, REPLICATE_API_TOKEN in the process environment, .env.local and .env).")
        if args.image_tool:
            print(f"Next: you have the built-in image tool '{args.image_tool}'. It needs no key. Run mock with --backend host, "
                  f"make 1 image for each printed prompt with '{args.image_tool}', and save each image at the printed path.")
        elif args.no_image_tool:
            print("Next: tell the user, in 1 or 2 friendly sentences: the mock stills need an image model. There are 2 ways to get one.")
            print("  1. Add an OpenAI key (OPENAI_API_KEY) or a Higgsfield key (HF_KEY) to .env.local.")
            print("  2. Paste the ready prompts into any image tool that the user has. Run mock with --backend text: it prints 1 copy-ready")
            print("     prompt and 1 file name for each option. Then register the images: mock --options PATH --import option_B=FILE.")
            print("Until then, the text diagrams and the prompts carry the session. Nothing is blocked.")
        else:
            print("Next: use the host's built-in image tool when it has one (--backend host), or the text-only mode (--backend text).")
            print("Say which case you are in: detect --image-tool NAME (for example image_gen in Codex) or detect --no-image-tool.")
        return 0
    for index, backend in enumerate(found):
        mark = "selected" if index == 0 else "available"
        model = backend["model"] or f"not set: set {backend['model_var']}"
        print(f"{backend['name']}: key found in {backend['source']} ({mark}); model: {model}")
        for name in (".env.local", ".env"):
            if backend["source"] == name and git_ignored(Path(args.cwd) / name) is False:
                print(f"  WARNING: {name} is not ignored by Git. Add it to .gitignore before you commit.")
    return 0


def cmd_prompt(args, env):
    """The fast path: the user knows what they want. One prompt, no options round."""
    techniques = None
    if args.technique:
        if args.technique not in C.TECHNIQUES:
            raise Refusal(f"Unknown technique '{args.technique}'. Known: {', '.join(sorted(C.TECHNIQUES))}.")
        techniques = distinct_families(C.FALLBACK + list(C.TECHNIQUES), 3, [args.technique])
    doc = build_options(args.phrase, args.subject, args.action, args.setting, args.aspect, 3, techniques)
    validate_doc(doc)
    choice = choose(doc, "A")
    first = doc["options"][0]
    print(f"{first['pro_term']}: {first['plain']}")
    print()
    print(choice["prompt_block"])
    print()
    print("One line:")
    print(choice["one_line"])
    if choice["anti_slop_findings"]:
        print("\nWatch for: " + " ".join(choice["anti_slop_findings"]))
    if args.out:
        out = Path(args.out)
        write_outputs(doc, out)
        write_json(out / "choice.json", choice)
        (out / "final_spec.md").write_text(render_choice(choice), encoding="utf-8")
        print(f"\nSaved in {out}. For other options: plan --phrase \"...\". For a mock still: mock --options {out / 'options.json'}.")
    return 0


def import_images(doc, out, items, log=print):
    """Register images that the user made with the pasted prompts. Returns {label: file name}."""
    by_label = {o["label"]: o for o in doc["options"]}
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    book, images = load_receipts(out), {}
    for item in items:
        name, _, source = item.partition("=")
        label = name.replace("option_", "")
        if label not in by_label or not source:
            raise Refusal(f"--import: write option_LABEL=FILE with a label from {', '.join(by_label)}.")
        try:
            data = Path(source).read_bytes()
        except OSError as exc:
            raise Refusal(f"Cannot read {source}: {exc}")
        suffix = image_suffix(data)
        if not suffix:
            raise Refusal(f"{source} is not 1 complete PNG, JPEG or WebP image.")
        target = out / f"option_{label}{suffix}"
        atomic_write(target, data)
        for old in out.glob(f"option_{label}.*"):
            if old.suffix in IMAGE_SUFFIXES and old != target:
                old.unlink()
        book[label] = {"option": label, "backend": "user", "model": None, "status": "imported", "file": target.name,
                       "prompt_sha256": _sha256(by_label[label]["image_prompt"].encode("utf-8")), "image_sha256": _sha256(data)}
        images[label] = target.name
        log(f"Option {label}: registered {target}")
    for option in doc["options"]:
        for existing in sorted(out.glob(f"option_{option['label']}.*")):
            if existing.suffix in IMAGE_SUFFIXES:
                images.setdefault(option["label"], existing.name)
    save_receipts(out, book)
    write_outputs(doc, out, images)
    return images


def cmd_plan(args, env):
    doc, out = _load_doc(args)
    findings = validate_doc(doc, args.max_images)
    write_outputs(doc, out)
    print(render_markdown(doc))
    _print_findings(findings)
    if doc.get("unknown_reference"):
        print("UNKNOWN REFERENCE. This tool has no recipe for it and did not guess. Next: find references with the user "
              "(shotspeak.py refs --query \"...\"), or ask what the viewer should feel.")
    if doc.get("vague"):
        print("LOOK NOT CLEAR. " + " ".join(doc["vague_reasons"]))
        print(f"Next: find the look in rounds (shotspeak.py round --options {out / 'options.json'} --base A --vary light), then lock it.")
    print(f"Saved: {out / 'options.json'} and {out / 'options.md'}")
    return 3 if findings else 0


def _print_findings(findings, notes=()):
    for note in notes:
        print(f"Note: {note}")
    if not findings:
        print("Anti-slop check: passed for every option.")
        return
    print("Anti-slop advice (keep a choice that is on purpose):")
    for label, items in findings.items():
        for item in items:
            print(f"  Option {label}: {item}")


def cmd_mock(args, env):
    doc, out = _load_doc(args)
    if args.out:
        out = Path(args.out)
    max_images = int(env_value(env, "SHOTSPEAK_MAX_IMAGES", args.max_images))
    notes = []
    findings = validate_doc(doc, max_images, notes)
    if args.import_image:
        images = import_images(doc, out, args.import_image)
        print(f"{len(images)} of {len(doc['options'])} options have an image in {out}. The cards in {out / 'options.md'} show them.")
        return 0
    backend = select_backend(env, args.backend, args.model, require_key=not args.dry_run)
    size = args.size or ASPECTS.get(doc.get("aspect", "16:9"), "1536x864")
    info = card(doc, backend, size, args.quality, env)
    if backend["key_var"] and backend["key_var"] not in env:
        info["key_missing"] = backend["key_var"]
    print_card(doc, info, out)
    if isinstance(doc.get("round"), dict):
        state = load_rounds(Path(doc["round"]["state"]) if Path(doc["round"]["state"]).is_absolute() else out.parent / "rounds.json")
        number, cap = doc["round"]["number"], int(env_value(env, "SHOTSPEAK_MAX_ROUNDS", doc["round"]["max_rounds"]))
        spent = sum(r.get("estimated_usd") or 0 for r in state["rounds"] if r.get("status") == "generated")
        print(f"Round:     {number} of {cap} at most. Decision under test: {doc['round']['vary']}.")
        print(f"Total:     {spent:.2f} USD estimated for the rounds before this one; "
              f"{spent + (info['estimated_total_usd'] or 0):.2f} USD with this round.")
        if number > cap:
            raise Refusal(f"Round {number} is above the cap of {cap} rounds. Lock the look, or ask the user to raise the cap (--max-rounds).")
        if backend["name"] == "text":
            print("No image backend: this round uses the text diagrams. Tell the user that the look is less certain without pictures.")
    _print_findings(findings, notes)
    name = backend["name"]
    if args.dry_run and name in ("text", "host"):
        print(f"\nDRY RUN. Nothing was sent and no file was written. Backend '{name}' makes no paid request.")
        return 0
    if name == "text":
        write_outputs(doc, out)
        print("\nNo image backend. Nothing was sent. The framing diagrams and the copy-ready prompts are in")
        print(f"  {out / 'options.md'}")
        print("To get mock stills: paste each prompt above into any image tool, and save each image with the file name under its prompt.")
        print(f"Then register the images: mock --options {out / 'options.json'} --import option_A=FILE --import option_B=FILE")
        print("Or add an OpenAI key (OPENAI_API_KEY) or a Higgsfield key (HF_KEY) to .env.local.")
        return 0
    if name == "host":
        write_outputs(doc, out)
        print("\nHost mode: this tool sends nothing. Generate 1 image for each prompt above with the host's built-in")
        print("image tool, then save each image at the path shown under its prompt.")
        return 0
    if args.dry_run:
        cost = "an unknown cost" if info["estimated_total_usd"] is None else f"about {info['estimated_total_usd']:.2f} USD"
        print(f"\nDRY RUN. Nothing was sent. Ask the user in 1 line: \"{info['images']} mock stills, {cost} - go?\"")
        print("After a clear yes, run again with")
        print(f"  --confirm {info['fingerprint']}")
        return 0
    if not args.confirm:
        print(f"\nNOT SENT. This is a paid request. Show the card to the user. After the user agrees, add --confirm {info['fingerprint']}")
        return 2
    if args.confirm != info["fingerprint"]:
        raise Refusal(f"--confirm does not match this card ({info['fingerprint']}). The card changed. Show the new card to the user.")
    if not backend["model"]:
        raise Refusal(f"No model selected for '{name}'. Set {backend['model_var']} or use --model.")
    if name == "openai":
        validate_size(size)
    if info["estimated_total_usd"] is None and not args.accept_unknown_cost:
        raise Refusal("The cost is unknown. " + info["basis"])
    max_usd = float(env_value(env, "SHOTSPEAK_MAX_USD", args.max_usd))
    if info["estimated_total_usd"] is not None and info["estimated_total_usd"] > max_usd:
        raise Refusal(f"The estimate of {info['estimated_total_usd']:.2f} USD is above the limit of {max_usd:.2f} USD (--max-usd).")
    write_outputs(doc, out)
    receipts = generate(doc, backend, env, out, size, args.quality, force=args.force)
    ok = sum(1 for r in receipts if r["status"] in DONE)
    if isinstance(doc.get("round"), dict):
        path = out.parent / "rounds.json"
        state = load_rounds(path)
        for entry in state["rounds"]:
            if entry["number"] == doc["round"]["number"]:
                entry.update({"status": "generated" if ok == len(doc["options"]) else "partial", "estimated_usd": info["estimated_total_usd"],
                              "measured_usd": round(sum(r.get("measured_usd_at_published_rates") or 0 for r in receipts), 6),
                              "images": [{"path": f"{out.name}/{r['file']}", "sha256": r.get("image_sha256")} for r in receipts
                                         if r["status"] in DONE]})
        write_json(path, state)
    print(f"\n{ok} of {len(doc['options'])} images are in {out}. Receipts: {out / 'receipts.json'}")
    return 0 if ok == len(doc["options"]) else 1


def cmd_deslop(args, env):
    if args.file:
        try:
            text = Path(args.file).read_text(encoding="utf-8")
        except OSError as exc:
            raise Refusal(f"Cannot read {args.file}: {exc}")
    else:
        text = args.text or sys.stdin.read()
    text = text.strip()
    if not text:
        raise Refusal("Give the prompt with --text, --file or standard input.")
    tells, rewritten = deslop(text)
    kept = scan(text, check_missing=True)[1]
    names = banned_names(text)
    if args.json:
        print(json.dumps({"tells": tells, "kept": kept, "named": names, "rewrite": rewritten}, indent=2))
        return 0
    if not tells and not names:
        print("No AI-slop tells found.")
    else:
        print(f"{len(tells)} AI-slop tell(s) found:\n")
        for category in ("composition", "lighting", "lens", "motion", "finish"):
            for tell in [t for t in tells if t["category"] == category]:
                also = "  (the prompt also forbids it)" if tell.get("contradiction") else ""
                print(f"[{category}] {tell['tell']}  <- {tell['evidence']}{also}")
                print(f"    Why it reads as AI: {tell['why']}")
                print(f"    Fix: {tell['fix']} Fine when: {tell['fine_when']}.")
        for name in names:
            print(f"[names] '{name}' is a product, model or protected title. Describe the look or the shape instead.")
    for tell in kept:
        print(f"[kept] {tell['tell']}  <- {tell['evidence']}: a choice ('{tell['because']}'). Not changed.")
    if rewritten == text:
        print("\nNothing to rewrite. The prompt is unchanged." if not names else "\nRemove the names. Nothing else to rewrite.")
        return 0
    print("\nREWRITE (a starting point; replace each [bracket] with a decision):\n")
    print(rewritten)
    return 0


def cmd_choose(args, env):
    doc, out = _load_doc(args)
    validate_doc(doc, 8)
    manifest_path = Path(args.previs) if args.previs else out / "previs" / "previs.json"
    manifest = None
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise Refusal(f"Cannot read {manifest_path}: {exc}")
    elif args.previs:
        raise Refusal(f"Cannot read {args.previs}.")
    choice = choose(doc, args.pick, args.mix, args.action, previs_for(manifest, args.pick), args.layout_ref)
    lock = None
    try:
        lock = json.loads((out / "look_lock.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    choice["lock"] = {"status": lock_status(choice, lock), "approval": (lock or {}).get("approval"), "locked_at": (lock or {}).get("locked_at")}
    out = Path(args.out) if args.out else out
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "choice.json", choice)
    (out / "final_spec.md").write_text(render_choice(choice), encoding="utf-8")
    print(render_choice(choice))
    print(f"Saved: {out / 'choice.json'} and {out / 'final_spec.md'}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="shotspeak", description="Plain words in, shot options out.")
    parser.add_argument("--cwd", default=".", help="Folder to look for .env.local and .env in.")
    parser.add_argument("--env-file", help="Read keys from this file in place of .env.local and .env.")
    sub = parser.add_subparsers(dest="command", required=True)

    dt = sub.add_parser("detect", help="Show the available image backend. Never prints a key.")
    dt.add_argument("--image-tool", metavar="NAME", help="The built-in image tool in your own tool list, for example image_gen.")
    dt.add_argument("--no-image-tool", action="store_true", help="Your tool list has no image tool and no image connector.")

    pr = sub.add_parser("prompt", help="Fast path: 1 final prompt for a phrase, with no options round.")
    pr.add_argument("--phrase", required=True)
    pr.add_argument("--subject")
    pr.add_argument("--action")
    pr.add_argument("--setting")
    pr.add_argument("--aspect", default="16:9", choices=sorted(ASPECTS))
    pr.add_argument("--technique", help="A technique id, when the user named the shot. Default: the closest match.")
    pr.add_argument("--out", help="Also save options.json, choice.json and final_spec.md in this folder.")

    lk = sub.add_parser("looks", help="List or search the look recipes: a named look as decisions, with no name in it.")
    lk.add_argument("--search", help="Words to search for: a film, a person, a genre, a feeling.")
    lk.add_argument("--json", action="store_true")

    def plan_args(p, need_phrase):
        p.add_argument("--phrase", required=need_phrase, help="The shot in the user's own words.")
        p.add_argument("--subject", help="Generic subject, for example 'a skateboarder'. No real names.")
        p.add_argument("--action", help="What the subject does, for example 'at the top of a jump'.")
        p.add_argument("--setting", help="The place, for example 'an empty car park at dusk'.")
        p.add_argument("--aspect", default="16:9", choices=sorted(ASPECTS))
        p.add_argument("--count", type=int, default=DEFAULT_COUNT, help="3 or 4 options.")
        p.add_argument("--techniques", help="Comma-separated technique ids to use in place of the automatic selection.")
        p.add_argument("--out", help="Output folder. Default: shotspeak_out/<phrase>.")
        p.add_argument("--max-images", type=int, default=DEFAULT_MAX_IMAGES, help="Hard cap on images in 1 run.")

    plan = sub.add_parser("plan", help="Write 3 to 4 distinct options for a phrase.")
    plan_args(plan, True)

    mock = sub.add_parser("mock", help="Print the mock card (--dry-run) or generate the stills (--confirm).")
    plan_args(mock, False)
    mock.add_argument("--options", help="An options.json from 'plan' (edited or not).")
    mock.add_argument("--backend", help="openai, higgsfield, fal, replicate, host or text. Default: the first key found, else text.")
    mock.add_argument("--model", help="Model id for the backend.")
    mock.add_argument("--size", help="WIDTHxHEIGHT. Default: from the aspect.")
    mock.add_argument("--quality", default="medium", choices=QUALITIES)
    mock.add_argument("--max-usd", type=float, default=DEFAULT_MAX_USD, help="Refuse above this estimate.")
    mock.add_argument("--dry-run", action="store_true", help="Print the prompts and the estimate. Send nothing.")
    mock.add_argument("--confirm", metavar="FINGERPRINT", help="The card fingerprint the user agreed to.")
    mock.add_argument("--accept-unknown-cost", action="store_true", help="The user accepted a cost this tool cannot estimate.")
    mock.add_argument("--force", action="store_true", help="Request every image again, also one that this exact request already made.")
    mock.add_argument("--import", dest="import_image", action="append", metavar="option_LABEL=FILE",
                      help="Register an image that the user made with a pasted prompt. Repeatable. Sends nothing.")

    de = sub.add_parser("deslop", help="Flag AI-slop tells in a prompt and print a rewrite.")
    de.add_argument("--text")
    de.add_argument("--file")
    de.add_argument("--json", action="store_true")

    ch = sub.add_parser("choose", help="Pick or mix options. Writes choice.json and final_spec.md.")
    ch.add_argument("--options", required=True)
    ch.add_argument("--pick", required=True, help="Option label, for example B.")
    ch.add_argument("--mix", action="append", help="PART=LABEL with PART in lens, light, grade, speed. Repeatable.")
    ch.add_argument("--action", help="Replace the action text in the final prompt.")
    ch.add_argument("--out")
    ch.add_argument("--previs", help="A previs.json. Default: previs/previs.json beside the options file, when it exists.")
    ch.add_argument("--layout-ref", action="store_true", help="Add the layout-reference line to the prompt block. Needs a previs.")

    def blender_args(p):
        p.add_argument("--blender", help="Path of the Blender program. Default: the BLENDER variable, PATH, the standard folders.")
        p.add_argument("--mcp-host", help=f"Host of the Blender MCP add-on. Default: {P.MCP_DEFAULT_HOST}.")
        p.add_argument("--mcp-port", type=int, help=f"Port of the Blender MCP add-on. Default: {P.MCP_DEFAULT_PORT}.")

    bd = sub.add_parser("blender-detect", help="Show the previs route: mcp, headless or none. Opens no window.")
    blender_args(bd)
    bd.add_argument("--json", action="store_true")

    pv = sub.add_parser("previs", help="Optional: a grey-box blocking previs for each option in a local Blender.")
    pv.add_argument("--options", required=True)
    pv.add_argument("--route", default="auto", choices=("auto", "mcp", "headless", "none"))
    pv.add_argument("--only", help="Comma-separated option labels, for example B or A,C. Default: every option.")
    pv.add_argument("--size", type=int, default=P.DEFAULT_LONG_EDGE, help="Long edge of the stills in pixels.")
    pv.add_argument("--no-animatic", action="store_true", help="Do not write the short movie of the camera move.")
    pv.add_argument("--timeout", type=int, default=P.DEFAULT_TIMEOUT, help="Seconds for 1 option before Blender is stopped.")
    pv.add_argument("--collect", action="store_true", help="After an MCP run: hash the files and write previs.json.")
    pv.add_argument("--out", help="Previs folder. Default: previs/ beside the options file.")
    blender_args(pv)

    rf = sub.add_parser("refs", help="Print search links for public reference sites. Opens nothing.")
    rf.add_argument("--query", required=True, help="The user's words, or a film, a person or a genre.")
    rf.add_argument("--json", action="store_true")

    rd = sub.add_parser("round", help="A round of 2 to 4 mock stills of 1 option that differ in 1 decision.")
    rd.add_argument("--options", required=True, help="The options.json from 'plan'.")
    rd.add_argument("--base", required=True, help="The option that every still of the round starts from.")
    rd.add_argument("--vary", choices=sorted(C.ROUND_VALUES), help="The 1 decision that changes. Without it, only --keep is saved.")
    rd.add_argument("--keep", action="append", help="DECISION=VALUE that the user picked in the round before. Repeatable.")
    rd.add_argument("--values", help="Comma-separated values. Default: the current value and 2 that are far from it.")
    rd.add_argument("--reject", action="append", help="DECISION=VALUE that the user rejected. Repeatable. It is not shown again.")
    rd.add_argument("--max-rounds", type=int, default=DEFAULT_MAX_ROUNDS, help="The cap on rounds. Raise it only when the user asks.")

    lo = sub.add_parser("lock", help="Lock the look that the user approved. Writes look_lock.json.")
    lo.add_argument("--options", required=True)
    lo.add_argument("--pick", required=True)
    lo.add_argument("--mix", action="append")
    lo.add_argument("--action")
    lo.add_argument("--approval", required=True, help="The user's own words of approval, exactly.")
    lo.add_argument("--ref", action="append", help="A reference link that the user chose. Provenance only. Repeatable.")
    lo.add_argument("--at", help="Time of the lock, ISO 8601. Default: now.")
    lo.add_argument("--out")

    sq = sub.add_parser("sequence", help="Several short shots in 1 generation, with exact cut times.")
    sq.add_argument("--options", required=True)
    sq.add_argument("--pick", required=True, help="The option that becomes the hero shot.")
    sq.add_argument("--pattern", default="coverage", choices=sorted(C.SEQUENCES))
    sq.add_argument("--seconds", type=float, default=10.0, help="Length of the whole clip.")
    sq.add_argument("--beats", help="What happens in each shot, separated by ';'. Default: [brackets] to replace.")
    sq.add_argument("--anchor", help="The object that the whole action stays near, for example 'the red sofa'.")
    sq.add_argument("--out")
    return parser


# --------------------------------------------------------------------------
# Blocking previs (optional). The mock stills never wait for it.
# --------------------------------------------------------------------------
def _detect_blender(args, env):
    return P.detect(args.blender or env_value(env, "BLENDER"),
                    args.mcp_host or env_value(env, "SHOTSPEAK_BLENDER_MCP_HOST"),
                    args.mcp_port or env_value(env, "SHOTSPEAK_BLENDER_MCP_PORT"))


def cmd_blender_detect(args, env):
    found = _detect_blender(args, env)
    if args.json:
        print(json.dumps(found, indent=2))
        return 0
    print(f"Previs route: {found['route']}")
    print(f"Reason: {found['reason']}")
    print(f"Blender: {found['blender'] or 'not found'}" + (f" (version {found['version']})" if found["version"] else ""))
    print(f"MCP add-on socket {found['mcp']['host']}:{found['mcp']['port']}: {'open' if found['mcp']['open'] else 'closed'}")
    if found["route"] == "mcp":
        print("Next: use --route mcp only when your tool list has a Blender MCP tool that runs Python code. If it has none, use --route headless.")
    elif found["route"] == "none":
        print("Next: skip the previs. Tell the user why. The mock stills do not need Blender.")
    return 0


def cmd_previs(args, env):
    doc, base = _load_doc(args)
    validate_doc(doc, 8)
    out = Path(args.out) if args.out else base / "previs"
    only = [x.strip() for x in args.only.split(",")] if args.only else None
    if only and not set(only) <= {o["label"] for o in doc["options"]}:
        raise Refusal(f"--only: no such option. Options: {', '.join(o['label'] for o in doc['options'])}.")
    if not 240 <= args.size <= 1920:
        raise Refusal("--size: use 240 to 1920 pixels.")
    found = _detect_blender(args, env)
    route = found["route"] if args.route == "auto" else args.route
    if route == "headless" and not (found["blender"] and found["version"]):
        raise Refusal("Route 'headless' needs a local Blender. " + found["reason"])
    try:
        plans = P.write_scripts(doc, out, only, args.size)
    except P.PrevisError as exc:
        raise Refusal(str(exc))
    statuses, skipped = {}, None
    if route == "none":
        skipped = found["reason"] if args.route == "auto" else "The previs was skipped on request (--route none)."
        for option, _plan, _script in plans:
            statuses[option["label"]] = ("skipped", None)
    elif route == "mcp" and not args.collect:
        print("PREVIS, MCP ROUTE. This tool did not start Blender. For each option, send this code through the")
        print("Blender MCP tool that runs Python code. Each block builds a new scene. It does not change the user's scene.")
        for option, _plan, script in plans:
            print(f"\n--- Option {option['label']}")
            print(P.mcp_snippet(script, script.parent), end="")
        print(f"\nThen run: shotspeak.py previs --options {args.options} --route mcp --collect")
        print("If the MCP tool fails or does not answer, run the same command with --route headless.")
        P.collect(doc, out, plans, route, found, {o["label"]: ("not_rendered", None) for o, _p, _s in plans})
        return 0
    elif route == "headless":
        for option, _plan, script in plans:
            ok, message = P.run_headless(found["blender"], script, script.parent, not args.no_animatic, args.timeout)
            if not ok:
                statuses[option["label"]] = ("failed", message)
            print(f"Option {option['label']}: {'rendered' if ok else 'FAILED'}", file=sys.stderr)
    manifest = P.collect(doc, out, plans, route, found, statuses, skipped)
    if skipped:
        print("PREVIS SKIPPED. " + skipped)
        print("The mock stills do not need Blender. Tell the user that the previs was skipped, and why.")
        print(f"The Blender scripts are saved in {out}. They run later in any Blender 4.2 or newer.")
        return 0
    print(f"BLOCKING PREVIS  route: {route}  Blender {found['version'] or '?'}")
    for entry in manifest["options"]:
        print("\n".join(P.describe(entry)))
    print(f"\nFiles are in {out}. Manifest: {out / 'previs.json'}")
    print("Use: " + P.USE_RULE)
    return 0 if all(e["status"] == "ok" for e in manifest["options"]) else 1


# --------------------------------------------------------------------------
# Sequence: several short shots in 1 generation
# --------------------------------------------------------------------------
MIN_SHOT_SECONDS = 1.0


def cut_times(weights, seconds):
    """Shot boundaries in seconds, rounded to 0.1 s. They add up to the clip length exactly."""
    total, edges, run = sum(weights), [0.0], 0.0
    for weight in weights[:-1]:
        run += weight
        edges.append(round(seconds * run / total, 1))
    edges.append(round(seconds, 1))
    return edges


def build_sequence(doc, pick, pattern="coverage", seconds=10.0, beats=None, anchor=None):
    by_label = {o["label"]: o for o in doc["options"]}
    if pick not in by_label:
        raise Refusal(f"No option '{pick}'. Options: {', '.join(by_label)}.")
    if pattern not in C.SEQUENCES:
        raise Refusal(f"Unknown pattern '{pattern}'. Use one of: {', '.join(sorted(C.SEQUENCES))}.")
    hero, spec = by_label[pick], C.SEQUENCES[pattern]
    rows = list(spec["shots"])
    if spec.get("hero_family") and C.TECHNIQUES.get(hero.get("technique"), {}).get("family") == spec["hero_family"]:
        slot = spec["hero_slot"]
        rows = [spec["move_row"] if r[1] == "HERO" else r for r in rows]
        rows[slot] = (rows[slot][0], "HERO", "HERO", rows[slot][3], "HERO", rows[slot][5])
    if not 4 <= seconds <= 30:
        raise Refusal("Use 4 to 30 seconds for a sequence. Read the length limit of your video tool first.")
    edges = cut_times([r[5] for r in rows], seconds)
    if min(b - a for a, b in zip(edges, edges[1:])) < MIN_SHOT_SECONDS:
        raise Refusal(f"{seconds:g} s is too short for {len(rows)} shots: a shot needs {MIN_SHOT_SECONDS:g} s or more.")
    if beats and len(beats) != len(rows):
        raise Refusal(f"Pattern '{pattern}' has {len(rows)} shots. Give {len(rows)} beats, separated by ';'.")
    for field, text in (("beat", " ".join(beats or [])), ("anchor", anchor or "")):
        problems = lint_prompt(text)
        if problems:
            raise Refusal(f"The {field} text {problems[0]}")
    ctx = doc_ctx(doc)
    choices = user_choices(ctx)
    people = P.people_count(ctx["subject"])
    shots = []
    for index, (role, size, camera, beat, speed, _weight) in enumerate(rows):
        is_hero = size == "HERO"
        shots.append({
            "n": index + 1, "role": role, "start_s": edges[index], "end_s": edges[index + 1],
            "seconds": round(edges[index + 1] - edges[index], 1), "hero": is_hero,
            "size_lens": f"{hero['pro_term']}, {hero['lens']}" if is_hero else size,
            "camera": f"{hero['movement']}; {hero['placement']}" if is_hero else camera,
            "beat": beats[index].strip() if beats else beat,
            "speed": hero["speed"]["prompt"] if is_hero else speed,
        })
    cuts = ", ".join(f"{t:g}" for t in edges[1:-1])
    tells = list(C.TECHNIQUES.get(hero.get("technique"), {}).get("slop_avoids", [])) + C.VIDEO_BASE_AVOID + ["slowmo_everywhere", "perfect_textures"]
    if not _airborne(hero, ctx):
        tells = [t for t in tells if t != "floating_bodies"]
    lines = [
        f"SEQUENCE: {seconds:g} s, {ctx['aspect']} frame. {len(shots)} shots joined by {len(shots) - 1} hard cuts at exactly {cuts} s.",
        "ONE ACTION AND ONE CAMERA MOVE IN EACH SHOT. Each cut comes when the motion of its shot ends.",
        f"SUBJECT AND ACTION: {ctx['subject']} {ctx['action']}, in {ctx['setting']}.",
        (f"PEOPLE: exactly {people}. " + ("Each person keeps 1 screen side for the whole clip. " if people > 1 else "")
         + ("" if "eyes_to_lens" in choices else "Nobody looks into the lens: the eyes stay on a target inside the scene.")).rstrip(),
        f"STAGE: the whole action stays within 2 m of {anchor or '[name 1 anchor object in the place]'}. "
        "The camera stays on 1 side of the action for every shot.",
        f"LIGHT: {hero['light']['prompt']}. The same light direction in every shot.",
        f"COLOUR: {hero['grade']['prompt']}. The same grade in every shot.",
        f"SPEED RULE: {spec['speed_rule']}.",
        "SHOT LIST:",
    ] + [f"  {s['n']}. {s['start_s']:g} to {s['end_s']:g} s | {s['size_lens']} | camera: {s['camera']} | action: {s['beat']} | speed: {s['speed']}"
         for s in shots] + [
        "FIRST FRAME: [where each person stands and what each person holds at 0 s].",
        "LAST FRAME: [where each person is at the end; hold it still]. Use this frame as the start of the next clip.",
        "AVOID: " + "; ".join(avoid_clauses(tells, choices)) + ".",
    ]
    block = medium_text("\n".join(lines), ctx)
    problems = lint_prompt(block)
    if problems:
        raise Refusal("The sequence prompt " + problems[0])
    return {"tool": "shot-speak", "version": VERSION, "phrase": doc["phrase"], "picked": pick, "pattern": pattern,
            "pattern_name": spec["name"], "plain": spec["plain"], "seconds": round(seconds, 1), "cut_times_s": edges[1:-1],
            "people": people, "shots": shots, "open_brackets": block.count("["), "prompt_block": block}


def render_sequence(seq):
    lines = [f"# Sequence: {seq['pattern_name']}", "", seq["plain"], "",
             f"Hero shot: option {seq['picked']}. Length: {seq['seconds']:g} s. Cuts at: {', '.join(f'{t:g}' for t in seq['cut_times_s'])} s.", "",
             "| # | Time | Shot | Camera | What happens | Speed |", "|---|---|---|---|---|---|"]
    lines += [f"| {s['n']} | {s['start_s']:g} to {s['end_s']:g} s | {s['size_lens']}" + (" (hero)" if s["hero"] else "")
              + f" | {s['camera']} | {s['beat']} | {s['speed']} |" for s in seq["shots"]]
    lines += ["", "## Prompt block", "", "```text", seq["prompt_block"], "```", ""]
    if seq["open_brackets"]:
        lines += [f"Replace each of the {seq['open_brackets']} `[brackets]` with a decision before you use the prompt.", ""]
    return "\n".join(lines)


def cmd_sequence(args, env):
    doc, out = _load_doc(args)
    validate_doc(doc, 8)
    beats = args.beats.split(";") if args.beats else None
    seq = build_sequence(doc, args.pick, args.pattern, args.seconds, beats, args.anchor)
    out = Path(args.out) if args.out else out
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "sequence.json", seq)
    (out / "sequence.md").write_text(render_sequence(seq), encoding="utf-8")
    print(render_sequence(seq))
    print(f"Saved: {out / 'sequence.json'} and {out / 'sequence.md'}")
    return 0


# --------------------------------------------------------------------------
# When the look is not clear: reference links, rounds of mock stills, the lock
# --------------------------------------------------------------------------
DEFAULT_MAX_ROUNDS = 3
SEARCH_URL = "https://duckduckgo.com/?q="
LOCK_PARTS = ("movement", "placement", "lens", "light", "grade", "speed")


def reference_links(query):
    """Search links for the public reference sites. This function builds text only. It opens nothing."""
    words = " ".join(query.split())
    if not words:
        raise Refusal("Give the words to search for with --query.")
    links = [{"source": name, "about": about, "rule": rule,
              "url": SEARCH_URL + urllib.parse.quote_plus(f"site:{site} {words}")} for name, site, about, rule in C.REFERENCE_SITES]
    links.append({"source": "Web search", "about": "A general search for stills and articles.", "rule": "Open pages only.",
                  "url": SEARCH_URL + urllib.parse.quote_plus(f"{words} film still cinematography")})
    return links


def cmd_refs(args, env):
    links = reference_links(args.query)
    if args.json:
        print(json.dumps(links, indent=2))
        return 0
    print(f"REFERENCE SEARCH LINKS for: {' '.join(args.query.split())}")
    print("This tool opened nothing. Each line is a search link for the user, or for your own web tool.\n")
    for link in links:
        print(f"{link['source']}: {link['about']} {link['rule']}")
        print(f"  {link['url']}")
    print("\nRules: links only. Never log in. Never download, store or share a still. Never send a still, a title or a link to a generator.")
    print("From each reference, take decisions in words: framing, camera height, lens, move, light, colour, speed.")
    return 0


def load_rounds(path):
    try:
        state = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    state.setdefault("rounds", [])
    state.setdefault("rejected", {})
    return state


def round_values(vary, base, rejected, wanted=None, ctx=None):
    """The 2 to 4 values of 1 decision that a round shows. Never a value that the user rejected."""
    if vary not in C.ROUND_VALUES:
        raise Refusal(f"--vary: use one of {', '.join(C.ROUND_VALUES)}.")
    known = {"light": list(C.LIGHTS), "grade": [g for g in C.GRADES if g != "teal_orange"], "speed": C.ROUND_VALUES["speed"],
             "lens": list(C.ROUND_VALUES["lens"]), "height": list(C.ROUND_VALUES["height"])}[vary]
    if wanted:
        bad = [v for v in wanted if v not in known]
        if bad:
            raise Refusal(f"Unknown {vary}: {', '.join(bad)}. Known: {', '.join(known)}.")
        again = [v for v in wanted if v in rejected]
        if again:
            raise Refusal(f"The user rejected {', '.join(again)} in an earlier round. Do not show a rejected idea again.")
        values = list(dict.fromkeys(wanted))
    else:
        current = base[vary]["key"] if vary in ("light", "grade", "speed") else None
        order = {"light": scene_lights(ctx or {}) + C.LIGHT_ORDER, "grade": C.GRADE_ORDER}.get(vary, known)
        values = [v for v in dict.fromkeys(([current] if current in known else []) + order) if v not in rejected][:3]
    if not 2 <= len(values) <= 4:
        raise Refusal(f"A round shows 2 to 4 values. {len(values)} are left for '{vary}'. Lock the look, or vary another decision.")
    return values


def apply_value(option, vary, value):
    """Set 1 decision of an option. Returns the plain words for that value."""
    try:
        if vary == "light":
            option["light"] = {"key": value, **{k: C.LIGHTS[value][k] for k in ("name", "plain", "prompt")}}
            return C.LIGHTS[value]["plain"]
        if vary == "grade":
            option["grade"] = {"key": value, **{k: C.GRADES[value][k] for k in ("name", "plain", "prompt")}}
            return C.GRADES[value]["plain"]
        if vary == "speed":
            option["speed"] = {"key": value, **{k: C.SPEEDS[value][k] for k in ("name", "plain", "prompt", "still")}}
            return C.SPEEDS[value]["plain"]
        if vary == "lens":
            option["lens"], option["lens_why"] = value, C.ROUND_VALUES["lens"][value]
            return option["lens_why"]
        if vary == "height":
            option["placement"], says = C.ROUND_VALUES["height"][value]
            return says
    except KeyError:
        pass
    raise Refusal(f"Unknown value '{value}' for '{vary}'.")


def refined_doc(doc, base_label, kept):
    """The option set with the decisions that the rounds settled written into the base option."""
    out = copy.deepcopy(doc)
    ctx = doc_ctx(out)
    for option in out["options"]:
        if option["label"] == base_label:
            for vary, value in kept.items():
                apply_value(option, vary, value)
            for field in PROMPT_FIELDS:  # a settled decision replaces any hand-written prompt of the base option
                option[field] = ""
            set_prompts(option, ctx)
    return out


def build_round(doc, base_label, vary, number, max_rounds=DEFAULT_MAX_ROUNDS, wanted=None, rejected=()):
    by_label = {o["label"]: o for o in doc["options"]}
    if base_label not in by_label:
        raise Refusal(f"No option '{base_label}'. Options: {', '.join(by_label)}.")
    if number > max_rounds:
        raise Refusal(f"Round {number} is above the cap of {max_rounds} rounds. Lock the look, or ask the user to raise the cap (--max-rounds).")
    base = by_label[base_label]
    ctx = doc_ctx(doc)
    options = []
    for index, value in enumerate(round_values(vary, base, set(rejected), wanted, ctx)):
        option = copy.deepcopy(base)
        says = apply_value(option, vary, value)
        option.update({"label": LABELS[index], "recommended": False, "variant_of": base_label, "varies": vary, "value": value,
                       "plain": says})
        option.pop("recommended_because", None)
        for field in PROMPT_FIELDS:  # each still of a round shows a changed decision: its prompts are rebuilt
            option[field] = ""
        set_prompts(option, ctx)
        options.append(option)
    return {"tool": "shot-speak", "version": VERSION, **ctx,
            "round": {"number": number, "vary": vary, "base": base_label, "max_rounds": max_rounds, "state": "rounds.json",
                      "values": [o["value"] for o in options]},
            "interpretation": [f"Round {number}: the same shot {len(options)} times. Only the {vary} changes."], "options": options}


def cmd_round(args, env):
    doc, base = _load_doc(args)
    validate_doc(doc, 8)
    if not args.vary and not args.keep:
        raise Refusal("Give --vary DECISION for a new round, or --keep DECISION=VALUE to save what the user picked.")
    state_path = base / "rounds.json"
    state = load_rounds(state_path)
    for item in args.reject or []:
        if "=" not in item:
            raise Refusal("Write each rejected value as DECISION=VALUE, for example light=high_key.")
        part, value = item.split("=", 1)
        state["rejected"].setdefault(part, [])
        if value not in state["rejected"][part]:
            state["rejected"][part].append(value)
    state.setdefault("kept", {})
    for item in args.keep or []:
        if "=" not in item:
            raise Refusal("Write each kept value as DECISION=VALUE, for example light=overcast_soft.")
        part, value = item.split("=", 1)
        apply_value(copy.deepcopy(doc["options"][0]), part, value)
        state["kept"][part] = value
    if state["kept"]:
        doc = refined_doc(doc, args.base, state["kept"])
        write_json(base / "refined.json", doc)
        print("Settled so far: " + "; ".join(f"{k}: {v}" for k, v in state["kept"].items()) + f". Saved in {base / 'refined.json'}.")
    if not args.vary:
        write_json(state_path, state)
        print(f"Next: choose or lock with --options {base / 'refined.json'} --pick {args.base}")
        return 0
    number = len(state["rounds"]) + 1
    cap = int(env_value(env, "SHOTSPEAK_MAX_ROUNDS", args.max_rounds))
    wanted = [v.strip() for v in args.values.split(",")] if args.values else None
    round_doc = build_round(doc, args.base, args.vary, number, cap, wanted, state["rejected"].get(args.vary, []))
    out = base / f"round_{number}"
    write_outputs(round_doc, out)
    state["rounds"].append({"number": number, "vary": args.vary, "base": args.base, "values": round_doc["round"]["values"],
                            "status": "planned", "estimated_usd": None, "measured_usd": None, "images": []})
    write_json(state_path, state)
    print(f"ROUND {number} of {cap} at most. The same shot (option {args.base}), {len(round_doc['options'])} times. Only the {args.vary} changes.")
    for option in round_doc["options"]:
        print(f"  {option['label']}: {option['value']} - {option['plain']}")
    if state["rejected"]:
        print("Rejected before, not shown again: " + "; ".join(f"{k}: {', '.join(v)}" for k, v in state["rejected"].items() if v))
    print(f"Saved: {out / 'options.json'}")
    print(f"Next: shotspeak.py mock --options {out / 'options.json'} --dry-run   (a paid request: show the card, get a clear yes)")
    print("With no image backend, add --backend text and show the text diagrams. Say that the look is less certain without pictures.")
    return 0


def spec_fingerprint(choice):
    spec = {part: choice["spec"][part] for part in LOCK_PARTS}
    return hashlib.sha256(json.dumps([spec, choice["prompt_block"]], sort_keys=True).encode("utf-8")).hexdigest()


def lock_status(choice, lock):
    """'LOCKED', 'STALE' or 'UNLOCKED' for a choice and the content of look_lock.json (or None)."""
    if not lock:
        return "UNLOCKED"
    return "LOCKED" if lock.get("spec_sha256") == spec_fingerprint(choice) else "STALE"


LOCK_LINES = {"UNLOCKED": "UNLOCKED: decisions may still change.",
              "STALE": "LOCK IS STALE: the decisions changed after the lock. Lock again with the user's approval.",
              "LOCKED": "LOCKED: the user approved these decisions."}


def build_lock(doc, choice, approval, base, references=(), locked_at=None):
    if not (approval or "").strip():
        raise Refusal("A lock needs the user's own words of approval (--approval). Never write them for the user.")
    for url in references:
        if not re.match(r"https?://\S+$", url):
            raise Refusal(f"--ref takes a link. '{url}' is not a link.")
    state = load_rounds(Path(base) / "rounds.json")
    mocks = []
    names = [f"option_{choice['picked']}.png"] + [image["path"] for r in state["rounds"] for image in r.get("images", [])]
    for name in names:
        path = Path(base) / name
        if path.is_file():
            mocks.append({"path": name, "sha256": P.sha256_file(path)})
    generated = [r for r in state["rounds"] if r.get("status") == "generated"]
    return {"tool": "shot-speak", "version": VERSION, "phrase": doc["phrase"], "picked": choice["picked"], "mixed": choice["mixed"],
            "locked": {part: choice["spec"][part] for part in LOCK_PARTS}, "look": doc.get("look"),
            "spec_sha256": spec_fingerprint(choice),
            "references": [{"url": url, "use": "provenance only; never in a prompt"} for url in references],
            "mocks": mocks,
            "rounds": {"planned": len(state["rounds"]), "generated": len(generated), "rejected": state["rejected"],
                       "estimated_usd": round(sum(r.get("estimated_usd") or 0 for r in generated), 4),
                       "measured_usd": round(sum(r.get("measured_usd") or 0 for r in generated), 6)},
            "approval": approval.strip(), "locked_at": locked_at}


def cmd_lock(args, env):
    doc, base = _load_doc(args)
    validate_doc(doc, 8)
    choice = choose(doc, args.pick, args.mix, args.action)
    lock = build_lock(doc, choice, args.approval, base, args.ref or [],
                      args.at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    out = Path(args.out) if args.out else base
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "look_lock.json", lock)
    print("LOOK LOCKED.")
    for part in LOCK_PARTS:
        print(f"  {part}: {lock['locked'][part]}")
    print(f"  rounds: {lock['rounds']['generated']} generated, {lock['rounds']['estimated_usd']:.2f} USD estimated")
    print(f"  references kept as provenance: {len(lock['references'])}. They are not in any prompt.")
    print(f"  approval: \"{lock['approval']}\"")
    print(f"Saved: {out / 'look_lock.json'}. Run 'choose' with the same --pick and --mix for the final spec. A change needs a new lock.")
    return 0


def cmd_looks(args, env):
    ids = list(C.LOOKS)
    if args.search:
        look_id, _text, _unknown = find_look("like " + args.search)
        words = [w for w in re.findall(r"[a-z0-9]+", args.search.lower()) if len(w) > 2]
        ids = [look_id] if look_id else [i for i in ids if any(
            w in (i + " " + C.LOOKS[i]["name"] + " " + C.LOOKS[i]["clause"]).lower() for w in words)]
    if args.json:
        print(json.dumps({i: C.LOOKS[i] for i in ids}, indent=2))
        return 0
    if not ids:
        print("No look recipe matches. This tool does not guess. Ask the user 1 question: what should the viewer feel?")
        return 0
    for i in ids:
        look = C.LOOKS[i]
        print(f"{i}: {look['name']}")
        print(f"  Shot: {C.TECHNIQUES[look['technique']]['pro_term']}. Light: {C.LIGHTS[look['light']]['name']}. Grade: {C.GRADES[look['grade']]['name']}.")
        for line in look["makes"]:
            print(f"  - {line}")
    print(f"\n{len(ids)} look recipe(s). Use: plan --phrase \"... like <the film, the person or the genre>\". The name does not reach a prompt.")
    return 0


COMMANDS = {"detect": cmd_detect, "prompt": cmd_prompt, "looks": cmd_looks, "plan": cmd_plan, "mock": cmd_mock,
            "deslop": cmd_deslop, "choose": cmd_choose, "blender-detect": cmd_blender_detect, "previs": cmd_previs,
            "refs": cmd_refs, "round": cmd_round, "lock": cmd_lock, "sequence": cmd_sequence}


def main(argv=None, environ=None):
    args = build_parser().parse_args(argv)
    env = {}
    try:
        env = load_env(args.cwd, args.env_file, environ)
        return COMMANDS[args.command](args, env)
    except Refusal as exc:
        print(redact(f"REFUSED: {exc}", secrets_of(env)), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
