#!/usr/bin/env python3
"""Rebuild the worked examples in ``examples/`` from the scripts' real output.

    python3 scripts/build_examples.py          # write the files
    python3 scripts/build_examples.py --check  # exit 1 when a file is stale

No network. No key. The examples use the text-only path.
"""

import contextlib
import io
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import previs as P  # noqa: E402
import shotspeak as S  # noqa: E402

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

PHRASE = "the bullet time thingy where the camera swishes around them mid-air"
SUBJECT = "two masked ninjas"
ACTION = "at the top of a jump off a low wall"
SETTING = "a walled courtyard at sunset"

BAD = ("cinematic shot of a skateboarder doing a kickflip, slow motion throughout, camera slowly orbiting around him, "
       "beautiful lighting, lens flares, ultra detailed, 4k")
GOOD = ("A skateboarder kickflips over a low concrete ledge, seen from a locked camera on the ground, side-on, 3 m away, "
        "the lens level; 18 mm lens, the rough concrete large in the foreground; one hard low sun behind him, his body "
        "rimmed with light, long shadows toward the lens, about a third of the frame in deep shadow; real time into the "
        "trick, a short ramp to slow motion at the top of the kickflip, then back to real time for the landing; his eyes "
        "stay on the board; fine grain, true blacks, worn dusty concrete. Avoid: nobody looks into the lens; no slow "
        "floating camera drift; no bloom, no haze, no fog; real gravity and real jump height, nobody floats.")


PARTS = [
    ("1-plan.md", "Step 1: plan", "the user's words become 4 options"),
    ("2-card.md", "Step 2: the card for option A, as shown in chat", "how 1 option looks in the chat"),
    ("3-mock-card.md", "Step 3: the mock card (dry run)", "the cost card before a paid request"),
    ("4-choose.md", "Step 4: choose", "the pick, the mix and the final prompt block"),
]


def example_one_parts(text):
    """Example 1 as small files: an index and 1 file for each step. Links point to ../bullet-time/."""
    sections = re.split(r"(?m)^(?=## )", text.replace("](bullet-time/", "](../bullet-time/"))
    assert len(sections) == 6, len(sections)
    head, words, steps = sections[0], sections[1], sections[2:]
    files = {}
    listing = "\n".join(f"- [{title}]({name}): Read when you want to see {what}." for name, title, what in PARTS)
    files["01-bullet-time/index.md"] = f"{head}{words}## The steps\n\n{listing}\n"
    for n, (name, title, what) in enumerate(PARTS):
        body = steps[n].replace(f"## {title}", f"# Example 1, {title[0].lower()}{title[1:]}", 1).rstrip()
        assert body.startswith("# Example 1, "), name
        nxt = f"[{PARTS[n + 1][1]}]({PARTS[n + 1][0]})" if n + 1 < len(PARTS) else "[Example 2: de-slop a prompt](../02-deslop.md)"
        files[f"01-bullet-time/{name}"] = f"{body}\n\n## See also\n\n- [Example 1: the steps](index.md): the user's words and the other steps\n- Next: {nxt}\n"
    return files


def bullet_time():
    doc = S.build_options(PHRASE, SUBJECT, ACTION, SETTING)
    findings = S.validate_doc(doc)
    assert not findings, findings
    choice = S.choose(doc, "A", ["grade=D"])
    o = {x["label"]: x for x in doc["options"]}
    a = o["A"]
    rows = "\n".join(
        f"| {x['label']} | {x['pro_term']} | {x['lens']} | {x['light']['name']} | {x['grade']['name']} | {x['speed']['name']} | {x['feel']} |"
        for x in doc["options"])
    text = f"""# Example 1: "the bullet time thingy"

A complete run, from the user's words to the final prompt block.
The files that the scripts wrote are in [`bullet-time/`](bullet-time/). No image was generated for this example.
It uses the text-only path, so you can reproduce it without a key: `python3 scripts/build_examples.py`.

## The user's words

> {PHRASE}

From the conversation, the agent also knows: 2 masked ninjas, a jump off a low wall, a walled courtyard at sunset.

## Step 1: plan

```sh
python3 scripts/shotspeak.py plan \\
  --phrase "{PHRASE}" \\
  --subject "{SUBJECT}" \\
  --action "{ACTION}" \\
  --setting "{SETTING}" \\
  --out examples/bullet-time
```

What the words mean in film language:

{chr(10).join(f"- {n}" for n in doc['interpretation'])}

The 4 options. Each one is a different technique family, with a different lens, light and grade:

| | Pro term | Lens | Light | Grade | Speed | The viewer feels |
|---|---|---|---|---|---|---|
{rows}

Recommended: **A**. {a['recommended_because']}

The script also printed:

```text
Note: {doc['note']}
Anti-slop check: passed for every option.
```

The complete cards, with the diagrams and the prompts, are in [`bullet-time/options.md`](bullet-time/options.md).

## Step 2: the card for option A, as shown in chat

**Option A: {a['pro_term']} (recommended)**

- **In plain words:** {a['plain']}
- **What the viewer feels:** {a['feel']}
- **Pro term to learn:** {a['pro_term']}
- **Choose it when:** {a['when']}
- **Camera movement:** {a['movement']}.
- **Camera placement:** {a['placement']}.
- **Lens:** {a['lens']}. {a['lens_why']}
- **Light:** {a['light']['name']}. {a['light']['plain']}
- **Colour grade:** {a['grade']['name']}. {a['grade']['plain']}
- **Speed:** {a['speed']['name']}. {a['speed']['plain']}
- **AI look it avoids:** {'; '.join(a['slop_avoided'])}.
- **Risks with AI video generators:**
{chr(10).join(f"  - {r}" for r in a['risks'])}
- **Say this to a video model:**

```text
{a['video_snippet']}
```

With no image backend, the card shows the text diagram:

```text
{S.diagram(a)}
```

Why about 130 degrees and not a half circle: at 180 degrees the camera passes the front of the faces, the
ninjas look into the lens, and their direction of travel flips on screen. The arc starts behind the shoulder
and stops at a front three-quarter view. The faces stay in profile and the direction holds.

## Step 3: the mock card (dry run)

```sh
python3 scripts/shotspeak.py mock --options examples/bullet-time/options.json --backend openai --dry-run
```

The dry run prints the 4 image prompts, then the cost card. Nothing is sent. The prompt for option A:

```text
{a['image_prompt']}
```

The end of the card (the fingerprint is the value for `--confirm`):

```text
Backend:   openai  (model {S.OPENAI_DEFAULT_MODEL})
Size:      1536x864   Quality: medium
Images:    4
Estimate:  {S.OPENAI_EST_USD_PER_IMAGE * 4:.2f} USD
Card:      <fingerprint>
```

The agent shows the count and the estimate, and waits for a clear yes.

## Step 4: choose

The user says: "A, but with the harsh silvery look of D."

```sh
python3 scripts/shotspeak.py choose --options examples/bullet-time/options.json --pick A --mix grade=D
```

The final prompt block ([`bullet-time/final_spec.md`](bullet-time/final_spec.md)):

```text
{choice['prompt_block']}
```

Before the user pastes it into a video generator, the agent adds what only the user knows: "exactly 2 people",
which ninja is on screen-left, and what each one wears.
"""
    return {
        **example_one_parts(text),
        "bullet-time/options.json": json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
        "bullet-time/options.md": S.render_markdown(doc),
        "bullet-time/choice.json": json.dumps(choice, indent=2, ensure_ascii=False) + "\n",
        "bullet-time/final_spec.md": S.render_choice(choice),
    }


def deslop():
    tells, rewrite = S.deslop(BAD)
    assert S.deslop(GOOD)[0] == [] and S.lint_prompt(GOOD) == []
    rows = "\n".join(f"| {t['category']} | {t['tell']} | {t['evidence']} | {t['why']} |" for t in tells)
    text = f"""# Example 2: de-slop a prompt

The user pastes a prompt and says: "My videos all look like AI. What is wrong with this?"

## The prompt

```text
{BAD}
```

## Step 1: find the tells

```sh
python3 scripts/shotspeak.py deslop --text "{BAD}"
```

The script finds {len(tells)} tells:

| Group | Tell | Found in the prompt | Why it reads as AI |
|---|---|---|---|
{rows}

"(not stated)" means that the prompt leaves the decision to the generator. The generator then uses its default.

The script's rewrite is a starting point. Each `[bracket]` is a decision that is still open:

```text
{rewrite}
```

## Step 2: the agent makes the decisions

The agent asks 1 question, because the answer changes the shot:

> Do you want the trick at normal speed with one short slow-down at the top (recommended, it keeps the
> energy), or the camera moving around him while time is frozen?

The user selects the first choice. The agent fills each bracket from the guides:

| Open decision | The agent's decision | From |
|---|---|---|
| Camera | Locked on the ground, side-on, 3 m away, the lens level | [`camera/placement.md`](../references/camera/placement.md): on the floor for scale, profile for action |
| Lens | 18 mm | [`camera/lens.md`](../references/camera/lens.md): wide, low and close for scale and energy |
| Light | One hard low sun behind him, a third of the frame in shadow | [`light-colour/lighting.md`](../references/light-colour/lighting.md): the camera faces into the light |
| Speed | Real time with a short ramp at the top | [`camera/speed.md`](../references/camera/speed.md): slow motion for 1 beat |
| Camera move | None. The orbit is removed. | [`quality/slop-lens-motion-finish.md`](../references/quality/slop-lens-motion-finish.md): a locked frame is stronger than a slow orbit |
| Finish | Fine grain, true blacks, worn concrete | [`quality/slop-lens-motion-finish.md`](../references/quality/slop-lens-motion-finish.md): no quality words |

## Step 3: the rewritten prompt

```text
{GOOD}
```

The agent runs `deslop` on the rewrite. Result: `No AI-slop tells found.`

## What changed, in plain words

- "Cinematic" and "ultra detailed, 4k" are gone. They gave no direction. The prompt now describes a film look: grain, true blacks, worn concrete.
- The slow orbit is gone. The camera is locked on the ground, and the trick carries the shot.
- The camera has a place: on the ground, from the side. The skater is not centred and does not face the lens.
- The light has a source: a low sun behind him. A third of the frame is dark.
- Slow motion is 1 short beat at the top of the trick, not the whole shot.
- The decorative lens flares are gone. A small natural flare can still appear, because the sun is in the frame.
"""
    return {"02-deslop.md": text}


# --------------------------------------------------------------------------
# Scenes: the 3 tiers of the README, each from the real tool output
# --------------------------------------------------------------------------
SCENES = [
    {"slug": "dog-bullet-time", "title": "The dog and the bone",
     "phrase": "I want my dog to do a bullet time thingy when I throw him a bone, dramatically",
     "subject": "a scruffy brown dog", "action": "at the top of a jump, about to catch a thrown bone",
     "setting": "a backyard lawn at sunset", "pick": "B", "mix": ["light=C"], "says": "B, but with the light from C",
     "bad": "epic cinematic shot of my dog catching a bone in bullet time, dramatic, slow motion throughout, camera slowly orbiting around him, beautiful lighting, ultra detailed, 4k",
     "bad_gets": "A dog in the centre of the frame that looks at you. A slow full orbit. Soft golden light on everything. The dog floats.",
     "plain": "A scruffy brown dog jumps to catch a bone that its owner throws, on a backyard lawn at sunset. The dog catches the bone at the top of the jump and lands.",
     "plain_gets": "A clear, correct event. The camera is at chest height, 5 m away, and it drifts a little. The light is even. It looks like a phone video.",
     "skill_gets": "The camera lies in the grass. The dog jumps over the frame against the low sun. 1 slow beat at the top, and the dog has weight."},
    {"slug": "skate-kickflip", "title": "The kid and the kickflip",
     "phrase": "my kid lands a skateboard trick and I want it to look like a skate video",
     "subject": "a kid on a skateboard", "action": "landing a kickflip off a low kerb",
     "setting": "an empty car park on a grey day", "pick": "A", "mix": [], "says": "A",
     "bad": "cinematic skateboarding shot, kid doing an awesome trick, smooth cinematic camera movement, bokeh background, lens flares, hyper realistic, 8k",
     "bad_gets": "A teenager in the centre, in slow motion, with a blurred background and flares from no light source. The board does not turn.",
     "plain": "A kid on a skateboard rolls toward a low kerb in an empty car park on a grey day, does a kickflip off the kerb and lands it.",
     "plain_gets": "The correct trick, seen from eye height and from far away. The kid is small in the frame. The speed is hard to feel.",
     "skill_gets": "A very wide lens on the ground, next to the kerb. The wheels pass close to the lens. The trick looks fast and high."},
    {"slug": "alley-fight", "title": "The punch in the alley",
     "phrase": "two guys fight in an alley and I want to feel every punch, raw and shaky",
     "subject": "two stunt fighters in plain dark clothes", "action": "trading blows, one hard right hook lands on the jaw",
     "setting": "a narrow brick alley at night", "pick": "B", "mix": [], "says": "B",
     "sequence": {"pattern": "impact", "seconds": 10.0, "anchor": "the green steel door",
                  "beats": ["both men still, one on each side of the frame, eyes on each other",
                            "the man on screen left throws a right hook: the first visible motion is the punch itself",
                            "the knuckles stop on the side of the jaw and the cheek gives",
                            "the head turns away from the fist, the shoulders follow, he takes one step back, and the cut comes when he stops",
                            "both men still again: one a step back on screen right with a hand on his jaw, one with his fist still up"]},
     "bad": "epic fight scene between two men in a dark alley, cinematic, dramatic lighting, slow motion, camera circling around them, wet street, volumetric fog, 4k",
     "bad_gets": "Two men who look the same and dance around each other in slow motion. No punch lands. A wet floor, fog, and a camera that circles.",
     "plain": "Two men fight in a narrow brick alley at night. One man throws a hard right hook. The punch lands on the other man's jaw, and he steps back.",
     "plain_gets": "A wide view of 2 small men. The punch is slow and soft, and it stops before the jaw. The camera does not help.",
     "skill_gets": "A tight side-on view of the jaw. The fist comes in slowly and lands at full speed. The frame kicks with the force."},
    {"slug": "birthday-candles", "title": "The birthday candles",
     "phrase": "grandma blows out the candles, zoom in slowly, make it warm and emotional",
     "subject": "an old woman", "action": "blowing out the candles on a birthday cake",
     "setting": "a small dark kitchen", "pick": "A", "mix": [], "says": "A",
     "bad": "beautiful emotional cinematic shot of grandma blowing out birthday candles, warm glow, soft golden glow, creamy bokeh, smiling at the camera, masterpiece",
     "bad_gets": "A smooth, perfect face that smiles into the lens. Everything glows. The candles light nothing.",
     "plain": "An old woman sits at a kitchen table in a small dark kitchen. A birthday cake with lit candles is in front of her. She breathes in and blows out the candles.",
     "plain_gets": "The correct moment from the front, at table height. The room is evenly lit, so the candles are not the light. It is flat.",
     "skill_gets": "The camera moves toward her from the side. The candles are the only light. When they go out, the frame goes dark."},
    {"slug": "named-look", "title": "\"Like that film\"",
     "phrase": "dramatic like the Godfather dinner scene",
     "subject": "an old man at the head of a long table", "action": "listening without a word",
     "setting": "a dark dining room", "pick": "A", "mix": [], "says": "A",
     "bad": "dramatic dinner scene like The Godfather, cinematic, moody, dramatic lighting, 4k",
     "bad_gets": "Many tools refuse the title. The others give a generic dark room with a man in the centre.",
     "plain": "An old man sits at the head of a long table in a dark dining room. He listens to the others and says nothing.",
     "plain_gets": "A man at a table, lit evenly from the front. You see his eyes, so there is no secret.",
     "skill_gets": "The light comes from straight above, so his eyes are in shadow. The room is black and amber. The camera creeps toward him."},
]


def capture(argv):
    """Run the real command line and return its exit code and standard output."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = S.main(argv, environ={})
    return code, out.getvalue()


def scene(spec):
    slug = spec["slug"]
    files = {}
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / slug
        shown = f"examples/{slug}"

        def run(argv):
            code, text = capture(["--cwd", tmp] + argv)
            assert code == 0, (slug, argv, code, text[-400:])
            return text.replace(str(work), shown).replace(tmp, "examples")

        plan_cmd = ["plan", "--phrase", spec["phrase"], "--subject", spec["subject"], "--action", spec["action"],
                    "--setting", spec["setting"], "--out", str(work)]
        options = str(work / "options.json")
        mix = [x for m in spec["mix"] for x in ("--mix", m)]
        # The committed previs manifest, when it exists, gives the final spec its previs section.
        manifest = EXAMPLES / slug / "previs" / "previs.json"
        previs = ["--previs", str(manifest)] if manifest.is_file() else []
        transcripts = {
            "detect": run(["detect"]),
            "plan": run(plan_cmd),
            "mock-dry-run": run(["mock", "--options", options, "--backend", "openai", "--dry-run"]),
            "choose": run(["choose", "--options", options, "--pick", spec["pick"]] + mix + previs),
        }
        if spec.get("sequence"):
            seq = spec["sequence"]
            transcripts["sequence"] = run(["sequence", "--options", options, "--pick", spec["pick"], "--pattern", seq["pattern"],
                                           "--seconds", str(seq["seconds"]), "--anchor", seq["anchor"], "--beats", ";".join(seq["beats"])])
        for name in ("options.json", "options.md", "choice.json", "final_spec.md", "sequence.json", "sequence.md"):
            if (work / name).exists():
                files[f"{slug}/{name}"] = (work / name).read_text(encoding="utf-8")
        for name, text in transcripts.items():
            files[f"{slug}/transcript/{name}.txt"] = text
    _code, deslop_text = capture(["deslop", "--text", spec["bad"], "--json"])
    found = json.loads(deslop_text)
    assert S.slop_tells(spec["plain"]) == [] and S.lint_prompt(spec["plain"]) == [], slug
    choice = json.loads(files[f"{slug}/choice.json"])
    doc = json.loads(files[f"{slug}/options.json"])
    option = next(o for o in doc["options"] if o["label"] == spec["pick"])
    tiers = {
        "slug": slug, "title": spec["title"], "phrase": spec["phrase"], "user_says": spec["says"],
        "commands": {
            "plan": f'python3 scripts/shotspeak.py plan --phrase "{spec["phrase"]}" --subject "{spec["subject"]}" '
                    f'--action "{spec["action"]}" --setting "{spec["setting"]}" --out examples/{slug}',
            "choose": f"python3 scripts/shotspeak.py choose --options examples/{slug}/options.json --pick {spec['pick']}"
                      + "".join(f" --mix {m}" for m in spec["mix"]),
        },
        "bad": {"prompt": spec["bad"], "what_you_get": spec["bad_gets"],
                "tells": [t["tell"] for t in found["tells"]], "named": found["named"], "image": f"docs/img/{slug}_bad.jpg"},
        "plain": {"prompt": spec["plain"], "what_you_get": spec["plain_gets"],
                  "missing": [t["tell"] for t in S.slop_tells(spec["plain"], check_missing=True)], "image": f"docs/img/{slug}_plain.jpg"},
        "skill": {"picked": spec["pick"], "mixed": choice["mixed"], "pro_term": choice["spec"]["pro_term"], "plain_words": option["plain"],
                  "feel": option["feel"], "look_makes": option.get("look_makes", []), "what_you_get": spec["skill_gets"],
                  "decisions": {"Camera movement": choice["spec"]["movement"], "Camera placement": choice["spec"]["placement"],
                                "Lens": choice["spec"]["lens"], "Light": choice["spec"]["light"],
                                "Colour grade": choice["spec"]["grade"], "Speed": choice["spec"]["speed"]},
                  "prompt_block": choice["prompt_block"], "one_line": choice["one_line"], "image_prompt": choice["image_prompt"],
                  "image": f"docs/img/{slug}_skill.jpg"},
    }
    files[f"{slug}/tiers.json"] = json.dumps(tiers, indent=2, ensure_ascii=False) + "\n"
    return files


UNCLEAR = {"slug": "unclear-look", "phrase": "make it feel epic but sad", "subject": "a lone hiker",
           "action": "reaching the top of a ridge", "setting": "a mountain ridge in cloud",
           "approval": "yes - the grey one from above. lock it", "at": "2026-11-15T12:00:00Z"}


def unclear():
    """A request with no clear picture: 2 rounds that each test 1 decision, then a lock. No image is generated."""
    spec, slug, files = UNCLEAR, UNCLEAR["slug"], {}
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / slug
        options, refined = str(work / "options.json"), str(work / "refined.json")

        def run(argv):
            code, text = capture(["--cwd", tmp] + argv)
            assert code == 0, (argv, code, text[-400:])
            return text.replace(str(work), f"examples/{slug}").replace(tmp, "examples")

        steps = [
            ("1-plan", ["plan", "--phrase", spec["phrase"], "--subject", spec["subject"], "--action", spec["action"],
                        "--setting", spec["setting"], "--out", str(work)]),
            ("2-refs", ["refs", "--query", "epic but sad lone figure mountain"]),
            ("3-round-1", ["round", "--options", options, "--base", "A", "--vary", "light"]),
            ("4-round-1-card", ["mock", "--options", str(work / "round_1" / "options.json"), "--backend", "openai", "--dry-run"]),
            ("5-round-2", ["round", "--options", options, "--base", "A", "--keep", "light=overcast_soft",
                           "--reject", "light=hard_backlight", "--vary", "height"]),
            ("6-round-2-card", ["mock", "--options", str(work / "round_2" / "options.json"), "--backend", "openai", "--dry-run"]),
            ("7-keep", ["round", "--options", options, "--base", "A", "--keep", "height=high"]),
            ("8-lock", ["lock", "--options", refined, "--pick", "A", "--approval", spec["approval"], "--at", spec["at"]]),
            ("9-choose", ["choose", "--options", refined, "--pick", "A"]),
        ]
        for name, argv in steps:
            files[f"{slug}/transcript/{name}.txt"] = run(argv)
        for name in ("options.json", "refined.json", "rounds.json", "look_lock.json", "choice.json", "final_spec.md",
                     "round_1/options.json", "round_2/options.json"):
            files[f"{slug}/{name}"] = (work / name).read_text(encoding="utf-8")
    return files


def stale_previs():
    """The committed previs manifests must match the scripts that this version generates."""
    bad = []
    for manifest in sorted(EXAMPLES.glob("*/previs/previs.json")):
        doc = json.loads((manifest.parent.parent / "options.json").read_text(encoding="utf-8"))
        ctx = {k: doc.get(k, "") for k in ("subject", "action", "setting", "aspect")}
        by_label = {o["label"]: o for o in doc["options"]}
        for entry in json.loads(manifest.read_text(encoding="utf-8"))["options"]:
            plan = P.solve(by_label[entry["label"]], ctx, max(entry["resolution"]))
            if P.sha256_text(P.render_script(plan)) != entry["script_sha256"]:
                bad.append(f"{manifest.parent.parent.name}/previs option {entry['label']} (run scripts/build_previs_examples.py)")
    return bad


def main():
    files = {**bullet_time(), **deslop()}
    for spec in SCENES:
        files.update(scene(spec))
    files.update(unclear())
    stale = []
    for name, text in files.items():
        path = EXAMPLES / name
        if "--check" in sys.argv:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path}")
    if "--check" in sys.argv:
        stale += stale_previs()
    if stale:
        print("stale: " + ", ".join(stale))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
