#!/usr/bin/env python3
"""Build the walkthrough from the committed example outputs. Nothing here is written by hand.

    python3 scripts/build_walkthrough.py          # write the files
    python3 scripts/build_walkthrough.py --check  # exit 1 when a file is stale

It writes:
  docs/walkthrough/data.json   all data of the interactive page
  docs/walkthrough/data.js     the same data for a page that is opened from disk
  docs/replay.svg              an animated replay of 1 session: CSS animation only, no script
  docs/img/*.jpg               grey placeholder images, only where no image exists yet
  README.md                    the text between the GENERATED markers

Every text comes from ``examples/``: the files that the real commands wrote. Python 3 standard library only.
No network. Run ``build_examples.py`` first, and ``build_previs_examples.py`` when you have a local Blender.
"""

import base64
import copy
import hashlib
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shotspeak as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
DOCS = ROOT / "docs"
MAIN = "dog-bullet-time"
TIER_SCENES = ["dog-bullet-time", "skate-kickflip", "alley-fight", "birthday-candles"]
QUESTION = "What should the viewer feel?"
ANSWER = "That my dog is a legend."
THUMB_LIMIT = 200_000  # bytes: a larger image is not embedded in the SVG


def read(path):
    return (EXAMPLES / path).read_text(encoding="utf-8")


def load(path):
    return json.loads(read(path))


# --------------------------------------------------------------------------
# Placeholder images
# --------------------------------------------------------------------------
# A grey 480x270 JPEG frame with 2 diagonals: "an image goes here". The standard library cannot write a JPEG,
# so the bytes are stored here.
PLACEHOLDER = base64.b64decode(
    "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")
PLACEHOLDER_SHA = hashlib.sha256(PLACEHOLDER).hexdigest()


def image_slots():
    slots = [f"{slug}_{tier}.jpg" for slug in TIER_SCENES for tier in ("bad", "plain", "skill")]
    return slots + [f"{MAIN}_option_{label}.jpg" for label in "ABCD"]


def is_placeholder(path):
    return not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() == PLACEHOLDER_SHA


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
def previs_of(slug, label):
    path = EXAMPLES / slug / "previs" / "previs.json"
    if not path.is_file():
        return None
    for entry in json.loads(path.read_text(encoding="utf-8"))["options"]:
        if entry["label"] == label and entry["status"] == "ok":
            files = {f["role"]: f"examples/{slug}/previs/{f['path']}" for f in entry["files"]}
            return {"files": files, "summary": entry["summary"], "notes": entry["notes"] + entry.get("hidden", []),
                    "lines": S.P.describe(entry)[1:4]}
    return None


def keep(text, wanted, limit=None):
    lines = [line for line in text.splitlines() if any(line.startswith(w) for w in wanted)]
    return lines[:limit] if limit else lines


def build_data():
    doc = load(f"{MAIN}/options.json")
    tiers = load(f"{MAIN}/tiers.json")
    transcripts = {name: read(f"{MAIN}/transcript/{name}.txt") for name in ("detect", "plan", "mock-dry-run", "choose")}
    for name in ("blender-detect", "previs"):
        path = EXAMPLES / MAIN / "transcript" / f"{name}.txt"
        transcripts[name] = path.read_text(encoding="utf-8") if path.is_file() else ""
    options = []
    for option in doc["options"]:
        options.append({
            "label": option["label"], "pro_term": option["pro_term"], "recommended": bool(option.get("recommended")),
            "recommended_because": option.get("recommended_because", ""), "plain": option["plain"], "feel": option["feel"],
            "when": option["when"],
            "decisions": {"Camera movement": option["movement"], "Camera placement": option["placement"],
                          "Lens": f"{option['lens']}. {option['lens_why']}",
                          "Light": f"{option['light']['name']}: {option['light']['plain']}",
                          "Colour grade": f"{option['grade']['name']}: {option['grade']['plain']}",
                          "Speed": f"{option['speed']['name']}: {option['speed']['plain']}", "Length": option["duration"]},
            "light_name": option["light"]["name"], "grade_name": option["grade"]["name"],
            "risks": option["risks"], "video_snippet": option["video_snippet"], "image_prompt": option["image_prompt"],
            "diagram": S.diagram(option), "image": f"docs/img/{MAIN}_option_{option['label']}.jpg",
            "previs": previs_of(MAIN, option["label"]),
        })
    # Every pick with every light and every grade: the reader can try a mix.
    mixes = {}
    labels = [o["label"] for o in doc["options"]]
    for pick in labels:
        for light in labels:
            for grade in labels:
                mix = ([f"light={light}"] if light != pick else []) + ([f"grade={grade}"] if grade != pick else [])
                choice = S.choose(doc, pick, mix)
                mixes[f"{pick}|{light}|{grade}"] = {
                    "command": f"python3 scripts/shotspeak.py choose --options examples/{MAIN}/options.json --pick {pick}"
                               + "".join(f" --mix {m}" for m in mix),
                    "spec": choice["spec"], "prompt_block": choice["prompt_block"], "one_line": choice["one_line"]}
    plan = transcripts["plan"]
    card = transcripts["mock-dry-run"]
    chosen = transcripts["choose"]
    session = [
        {"who": "user", "text": tiers["phrase"] + "."},
        {"who": "agent", "text": QUESTION, "note": "At most 1 question, and only when the answer changes the options."},
        {"who": "user", "text": ANSWER},
        {"who": "tool", "title": "plan", "command": tiers["commands"]["plan"],
         "lines": keep(plan.split("## Option", 1)[0], ("**What your words", "- ", "Subject:", "Note:")) + keep(plan, ("## Option",))},
        {"who": "tool", "title": "anti-slop check", "command": "", "lines": keep(plan, ("Anti-slop check",))},
        {"who": "tool", "title": "mock --dry-run",
         "command": f"python3 scripts/shotspeak.py mock --options examples/{MAIN}/options.json --backend openai --dry-run",
         "lines": keep(card, ("Backend:", "Size:", "Images:", "Estimate:", "Card:", "DRY RUN"))},
        {"who": "cards", "title": "4 options"},
        {"who": "user", "text": tiers["user_says"]},
        {"who": "tool", "title": "choose", "command": tiers["commands"]["choose"],
         "lines": keep(chosen, ("# Final", "Picked:", "**UNLOCKED", "| Camera", "| Lens", "| Light", "| Colour", "| Speed", "SHOT:", "SUBJECT",
                                "LIGHT:", "SPEED:"))},
    ]
    scenes = []
    for slug in TIER_SCENES + ["named-look"]:
        entry = load(f"{slug}/tiers.json")
        entry["previs"] = previs_of(slug, entry["skill"]["picked"])
        for tier in ("bad", "plain", "skill"):
            if not (ROOT / entry[tier]["image"]).is_file():
                entry[tier]["image"] = None  # the page shows a note, not a broken picture
        scenes.append(entry)
    unclear = {name: read(f"unclear-look/transcript/{name}.txt") for name in
               ("1-plan", "3-round-1", "4-round-1-card", "5-round-2", "8-lock", "9-choose")}
    return {"tool": "shot-speak", "version": S.VERSION, "example": MAIN, "phrase": tiers["phrase"],
            "subject": doc["subject"], "action": doc["action"], "setting": doc["setting"],
            "interpretation": doc["interpretation"], "session": session, "options": options, "mixes": mixes,
            "picked": {"pick": tiers["skill"]["picked"], "mixed": tiers["skill"]["mixed"]},
            "transcripts": transcripts, "scenes": scenes, "unclear": unclear,
            "use_rule": S.P.USE_RULE}


# --------------------------------------------------------------------------
# The animated SVG replay
# --------------------------------------------------------------------------
W, H = 900, 560
FRAME_SECONDS = [4, 4, 3, 7, 3, 6, 8, 4, 9]


def clip(text, width=104):
    text = text.replace("**", "")
    return text if len(text) <= width else text[:width - 1] + "…"


def thumb_uri(data, option):
    """A small picture for an option card: the mock still when a small copy exists, else the previs still."""
    small = DOCS / "img" / "thumb" / f"{MAIN}_option_{option['label']}.jpg"
    if small.is_file() and small.stat().st_size <= THUMB_LIMIT:
        return "data:image/jpeg;base64," + base64.b64encode(small.read_bytes()).decode("ascii"), "mock still"
    if option["previs"]:
        path = ROOT / option["previs"]["files"]["still_mid"]
        if path.is_file() and path.stat().st_size <= THUMB_LIMIT:
            return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii"), "blocking previs"
    return None, "text diagram"


def build_svg(data):
    total = sum(FRAME_SECONDS)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
           f'aria-labelledby="t d">',
           '<title id="t">shot-speak session replay</title>',
           f'<desc id="d">An animated replay of a shot-speak session: {html.escape(data["phrase"])}. The user describes a shot, '
           'the tool plans 4 options, checks them, shows the cost, shows 4 cards, and writes the final prompt.</desc>',
           "<style>",
           "text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13px;fill:#d8dee9}",
           ".h{fill:#8fbcbb;font-weight:bold}.u{fill:#ebcb8b}.a{fill:#a3be8c}.c{fill:#88c0d0}.dim{fill:#7b8496}.w{fill:#eceff4}",
           ".big{font-size:17px;font-family:system-ui,-apple-system,Segoe UI,sans-serif}",
           ".f{opacity:0;animation-duration:%ds;animation-iteration-count:infinite;animation-timing-function:linear}" % total]
    start = 0
    for index, seconds in enumerate(FRAME_SECONDS):
        a, b = 100 * start / total, 100 * (start + seconds) / total
        fade = 100 * 0.4 / total
        out.append(f"@keyframes k{index}{{0%,{max(0, a - 0.01):.2f}%{{opacity:0}}{a + fade:.2f}%,{b - fade:.2f}%{{opacity:1}}"
                   f"{b:.2f}%,100%{{opacity:0}}}}")
        out.append(f".f{index}{{animation-name:k{index}}}")
        start += seconds
    out.append(f"@keyframes bar{{from{{width:0}}to{{width:{W - 40}px}}}}")
    out.append(f".bar{{animation:bar {total}s linear infinite}}")
    out.append("@media (prefers-reduced-motion:reduce){.f{animation:none}.f8{opacity:1}.bar{animation:none}}")
    out.append("</style>")
    out.append(f'<rect width="{W}" height="{H}" rx="10" fill="#1d2330"/>')
    out.append(f'<rect width="{W}" height="34" rx="10" fill="#2b3345"/><rect y="24" width="{W}" height="10" fill="#2b3345"/>')
    out.append('<circle cx="20" cy="17" r="6" fill="#bf616a"/><circle cx="40" cy="17" r="6" fill="#ebcb8b"/>'
               '<circle cx="60" cy="17" r="6" fill="#a3be8c"/>')
    out.append(f'<text x="{W / 2}" y="22" text-anchor="middle" class="dim">shot-speak: a session replay (real tool output)</text>')
    out.append(f'<rect x="20" y="{H - 14}" width="{W - 40}" height="3" fill="#2b3345"/>'
               f'<rect class="bar" x="20" y="{H - 14}" height="3" fill="#88c0d0"/>')

    def frame(index, lines):
        out.append(f'<g class="f f{index}">')
        y = 66
        for css, text in lines:
            if text is None:
                y += 10
                continue
            out.append(f'<text x="24" y="{y}" class="{css}" xml:space="preserve">{html.escape(clip(text))}</text>')
            y += 26 if "big" in css else 19
        out.append("</g>")

    session = data["session"]
    user = [("h", "YOU"), ("u big", clip(session[0]["text"], 92))]
    frame(0, user)
    frame(1, user + [("", None), ("h", "AGENT"), ("a big", session[1]["text"]), ("dim", session[1]["note"])])
    frame(2, user + [("", None), ("h", "AGENT"), ("a big", session[1]["text"]), ("", None), ("h", "YOU"), ("u big", session[2]["text"])])
    plan = session[3]
    frame(3, [("c", "$ shotspeak.py plan --phrase \"" + clip(data["phrase"], 60) + "\" ...")] + [("", None)]
          + [("w" if line.startswith("## ") else "", line) for line in plan["lines"]])
    frame(4, [("c", "$ shotspeak.py plan ...   (the check runs before any image)"), ("", None)]
          + [("a big", line) for line in session[4]["lines"]]
          + [("", None), ("dim", "The check looks for the generic AI look: a centred face, a soft glow, a slow orbit, slow motion everywhere.")])
    frame(5, [("c", "$ shotspeak.py mock --options options.json --dry-run"), ("", None)]
          + [("", line) for line in session[5]["lines"]]
          + [("", None), ("h", "AGENT"), ("a big", "4 mock stills, about 0.28 USD - go?")])
    # The 4 cards
    out.append('<g class="f f6">')
    out.append('<text x="24" y="62" class="h">AGENT   4 different ways to shoot it</text>')
    card_w, gap = 205, 12
    for n, option in enumerate(data["options"]):
        x = 24 + n * (card_w + gap)
        uri, kind = thumb_uri(data, option)
        out.append(f'<rect x="{x}" y="76" width="{card_w}" height="400" rx="6" fill="#2b3345" '
                   f'stroke="{"#a3be8c" if option["recommended"] else "#3b4458"}" stroke-width="2"/>')
        if uri:
            out.append(f'<image x="{x + 6}" y="82" width="{card_w - 12}" height="{(card_w - 12) * 9 / 16:.0f}" href="{uri}"/>')
        else:
            out.append(f'<rect x="{x + 6}" y="82" width="{card_w - 12}" height="{(card_w - 12) * 9 / 16:.0f}" fill="#3b4458"/>')
        out.append(f'<text x="{x + 10}" y="206" class="dim" style="font-size:10px">{kind}</text>')
        out.append(f'<text x="{x + 10}" y="228" class="w" style="font-weight:bold">{option["label"]}'
                   f'{"  (recommended)" if option["recommended"] else ""}</text>')
        y = 248
        for text in wrap(option["pro_term"], 22, 2):
            out.append(f'<text x="{x + 10}" y="{y}" class="c">{html.escape(text)}</text>')
            y += 17
        y += 6
        for text in wrap(option["plain"], 28, 6):
            out.append(f'<text x="{x + 10}" y="{y}" style="font-size:11.5px">{html.escape(text)}</text>')
            y += 15
        y += 6
        for text in wrap(option["decisions"]["Lens"].split(".")[0] + " | " + option["light_name"], 28, 3):
            out.append(f'<text x="{x + 10}" y="{y}" class="dim" style="font-size:11px">{html.escape(text)}</text>')
            y += 14
    out.append(f'<text x="24" y="{H - 54}" class="a big">Pick 1, mix parts of 2, or ask for other options.</text>')
    out.append("</g>")
    frame(7, [("h", "YOU"), ("u big", session[7]["text"])])
    choose = session[8]
    frame(8, [("c", "$ shotspeak.py choose --options options.json --pick "
               + data["picked"]["pick"] + "".join(f" --mix {k}={v}" for k, v in data["picked"]["mixed"].items())), ("", None)]
          + [("w" if line.startswith("# ") else "a" if line[:5] in ("SHOT:", "SUBJE", "LIGHT", "SPEED") else "", line) for line in choose["lines"]])
    out.append("</svg>")
    return "\n".join(out) + "\n"


def wrap(text, width, max_lines):
    words, lines, line = text.split(), [], ""
    for word in words:
        if len(line) + len(word) + 1 > width and line:
            lines.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][:width - 1] + "…"
    return lines


# --------------------------------------------------------------------------
# README sections
# --------------------------------------------------------------------------
def fence(text, lang="text"):
    return f"```{lang}\n{text.rstrip()}\n```"


MORE_EXAMPLES = [("dog-bullet-time", "dog"), ("skate-kickflip", "kickflip"), ("alley-fight", "alley fight"),
                 ("birthday-candles", "birthday candles")]


SHOT_LINE = re.compile(r"^(\d+)\. ([\d.]+) to ([\d.]+) s \| (HERO: )?(.+? mm),[^|]*\| ([^|]+)")


def prompt_shots(prompt):
    """The shots of a sent sequence prompt: the shot list in the text is the source, not the plan the tool first wrote."""
    shots = [m for m in map(SHOT_LINE.match, prompt.splitlines()) if m]
    return [{"n": int(m[1]), "start_s": float(m[2]), "end_s": float(m[3]), "hero": bool(m[4]), "size_lens": m[5], "beat": m[6].strip()}
            for m in shots]


def readme_examples(_data):
    """The real-video example: the 3 prompts, the 3 videos and the shot-speak decisions, all from examples/bike-cliff/."""
    base = EXAMPLES / "bike-cliff"
    tiers = json.loads((base / "tiers.json").read_text(encoding="utf-8"))
    options = json.loads((base / "options.json").read_text(encoding="utf-8"))
    sequence = json.loads((base / "sequence.json").read_text(encoding="utf-8"))
    by_label = {o["label"]: o for o in options["options"]}
    option = copy.deepcopy(by_label[sequence["picked"]])
    for part, label in tiers.get("mix", {}).items():  # the same pick-and-mix as `shotspeak.py choose --mix`
        option[part] = by_label[label][part]
    title, rows = tiers["title"], tiers["tiers"]
    prompts = {row["key"]: (ROOT / row["prompt"]).read_text(encoding="utf-8").strip() for row in rows}
    shots = prompt_shots(prompts["skill"])
    out = [f"![{title}: the 3 videos side by side, in sync]({tiers['compare_gif']})", "",
           "Full-quality MP4s with sound: " + " · ".join(f"[prompt {n + 1}]({r['video']})" for n, r in enumerate(rows)), "",
           f"> {tiers['phrase']}", "",
           "| " + " | ".join([""] + [r["label"] for r in rows]) + " |", "|---|---|---|---|",
           "| **What you get** | " + " | ".join(r["what_you_get"] for r in rows) + " |", "",
           "Same model, same face reference, 1 take each. Only the prompt changed. The 2 commands and the plan are in "
           "[`examples/bike-cliff/`](examples/bike-cliff/).", "",
           "<details>", "<summary>The 3 prompts and the shot-speak decisions</summary>", "",
           "**1. The first prompt**", "", fence(prompts["noob"]), "",
           "**2. A clear prompt with no film language**", "", fence(prompts["plain"]), "",
           f"**3. shot-speak: option {option['label']} ({option['pro_term']}), {sequence['pattern_name'].lower()}**", "",
           f"In plain words: {sequence['plain']} The hero shot is option {option['label']}: {option['plain']}", "",
           "| Decision | Value |", "|---|---|",
           f"| Camera movement | {option['movement']} |", f"| Camera placement | {option['placement']} |",
           f"| Lens | {option['lens']} |", f"| Light | {option['light']['name']} |",
           f"| Colour grade | {option['grade']['name']} |", f"| Speed | {option['speed']['name']} |", "",
           f"The {len(shots)} shots, with hard cuts at " + ", ".join(f"{s['end_s']:g}" for s in shots[:-1]) + " s:", "",
           "| # | Time | Shot | What happens |", "|---|---|---|---|"]
    out += [f"| {s['n']} | {s['start_s']:g} to {s['end_s']:g} s | {s['size_lens']}{' (hero)' if s['hero'] else ''} | {s['beat']} |"
            for s in shots]
    out += ["", "The prompt as sent, without the `@Image1` lines of the face reference:", "", fence(prompts["skill"]), "", "</details>", "",
            "More examples with mock stills: " + ", ".join(f"[{name}](examples/{slug}/)" for slug, name in MORE_EXAMPLES) + ".", ""]
    return "\n".join(out)


def details(title, body):
    return f"<details><summary><b>{title}</b></summary>\n\n{body}\n</details>\n"


def readme_walkthrough(data):
    t = data["transcripts"]
    recommended = next(o for o in data["options"] if o["recommended"])
    picked = data["mixes"]["|".join([data["picked"]["pick"], data["picked"]["mixed"].get("light", data["picked"]["pick"]),
                                     data["picked"]["mixed"].get("grade", data["picked"]["pick"])])]
    plan_lines = (keep(t["plan"].split("## Option", 1)[0], ("**What your words", "- ", "Note:"))
                  + keep(t["plan"], ("Anti-slop",)))
    steps = [
        ("1. Listen", f"> {data['phrase']}.\n\nThe agent asks 1 question at most: \"{QUESTION}\" Answer: \"{ANSWER}\""),
        ("2. Which image backend is here?", fence("python3 scripts/shotspeak.py detect", "sh") + "\n"
         + "With a key, the tool makes the stills. In Codex, the built-in `image_gen` tool makes them. With neither, you paste the prompts into any image tool."),
        ("3. Plan: the words become 4 options", fence(data["session"][3]["command"], "sh") + "\n\n" + fence("\n".join(plan_lines))
         + f"\nThe complete cards: [`examples/{MAIN}/options.md`](examples/{MAIN}/options.md)."),
        ("4. The cost question", fence(data["session"][5]["command"], "sh") + "\n\n"
         + fence("\n".join(keep(t["mock-dry-run"], ("Estimate:", "Card:", "DRY RUN", "  --confirm"))))
         + "\nNothing is sent before a clear yes."),
        ("5. An option card", f"**Option {recommended['label']}: {recommended['pro_term']} (recommended)**\n\n"
         f"![Mock still of option {recommended['label']}]({recommended['image']})\n\n"
         f"- **In plain words:** {recommended['plain']}\n- **What the viewer feels:** {recommended['feel']}\n"
         + "- **Risks with AI video generators:** " + " ".join(recommended["risks"])),
    ]
    if t["previs"]:
        steps.append(("6. Blocking previs (optional, free, local Blender)",
                      fence(f"python3 scripts/shotspeak.py previs --options examples/{MAIN}/options.json", "sh")
                      + f"\nThe frames are in example 1. {data['use_rule']}"))
    steps.append((f"{len(steps) + 1}. Pick and mix", f"> {data['session'][7]['text']}\n\n" + fence(picked["command"], "sh")
                  + f"\nThe final prompt block: [`examples/{MAIN}/final_spec.md`](examples/{MAIN}/final_spec.md)."))
    return "".join(details(title, body) for title, body in steps)


def readme_look(data):
    scene = next(s for s in data["scenes"] if s["slug"] == "named-look")
    skill = scene["skill"]
    return "\n".join([f"> {scene['phrase']}", "", "What makes that look, as the card says it:", ""]
                     + [f"- {m}" for m in skill["look_makes"]] + [
                         "", "The prompt that leaves the tool has no title and no name in it. "
                         "The full prompt: [`examples/named-look/final_spec.md`](examples/named-look/final_spec.md).", ""])


def readme_unclear(data):
    u = data["unclear"]
    return "\n".join([
        "> make it feel epic but sad", "",
        "`plan` prints `LOOK NOT CLEAR` here: the words name a mood, not a picture. Round 1 tests the light. The same shot, 3 times:", "", fence("\n".join(keep(u["3-round-1"], ("ROUND", "  A:", "  B:", "  C:")))), "",
        "The user: \"the grey one. Not the sunset, that is too pretty.\" Round 2 keeps the grey light and tests the camera height."
        " A rejected value is not shown again:", "",
        fence("\n".join(keep(u["5-round-2"], ("Settled", "ROUND", "Rejected")))), "",
        "The user: \"yes - the grey one from above. lock it\"", "",
        fence("\n".join(keep(u["8-lock"], ("LOOK LOCKED", "  placement", "  lens", "  light", "  grade")))), "",
        "The files are in [`examples/unclear-look/`](examples/unclear-look/). No image was generated for this example.", ""])


SECTIONS = {"examples": readme_examples, "walkthrough": readme_walkthrough, "look": readme_look, "unclear": readme_unclear}


def render_readme(text, data):
    for name, build in SECTIONS.items():
        begin, end = f"<!-- BEGIN GENERATED: {name} -->", f"<!-- END GENERATED: {name} -->"
        if begin not in text or end not in text:
            raise SystemExit(f"README.md has no '{name}' markers.")
        head, rest = text.split(begin, 1)
        _old, tail = rest.split(end, 1)
        text = head + begin + "\n" + build(data).rstrip() + "\n" + end + tail
    return text


def main():
    check = "--check" in sys.argv
    data = build_data()
    text = json.dumps(data, indent=1, ensure_ascii=False) + "\n"
    files = {
        DOCS / "walkthrough" / "data.json": text,
        DOCS / "walkthrough" / "data.js": "// Generated by scripts/build_walkthrough.py from examples/. Do not edit.\nwindow.WALKTHROUGH = "
                                            + text.rstrip() + ";\n",
        DOCS / "replay.svg": build_svg(data),
        ROOT / "README.md": render_readme((ROOT / "README.md").read_text(encoding="utf-8"), data),
    }
    stale = []
    for path, content in files.items():
        if check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"wrote {path.relative_to(ROOT)}")
    for name in image_slots():
        path = DOCS / "img" / name
        if not path.is_file():
            if check:
                stale.append(f"docs/img/{name}")
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(PLACEHOLDER)
                print(f"wrote placeholder docs/img/{name}")
    if stale:
        print("stale: " + ", ".join(stale))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
