---
name: shot-speak
description: Turn a shot described in everyday words into real film language. Use when someone who does not know camera terms describes a shot, a camera move or a look for a video or an AI video prompt - "that swishy movement", "the bullet time thingy", "make it look dramatic", "zoom in on them in slo-mo", "the camera goes around them", "like a movie", "like that film" - or asks what a shot is called, which lens or lighting to use, or why their AI video looks fake, generic or "AI". Gives 3-4 distinct options (camera move, placement, lens, light, colour grade, speed), 1 mock still for each option, plain-language explanations, a model-agnostic prompt line, and a final shot spec. Also turns a named film look into name-free decisions, plans multi-shot action sequences, builds an optional Blender blocking previs, and checks and rewrites a pasted video prompt to remove AI-slop defaults in composition, lighting, lens and motion.
---

# shot-speak

The user knows what they want to feel. They do not know what it is called. Give them the words, a picture
and a prompt that works in any video generator.

`SKILL_DIR` is the folder that holds this file. Run each script with `python3` (standard library only).

## Spirit

You are an enabler, not a gatekeeper. The steps below are a map. They are not a checklist.
Skip, reorder or shorten them when the user's intent is clear. Short answers are good.

**4 hard gates. Only these stop you:**

1. **A clear yes before money is spent.** Ask in 1 line: "4 mock stills, about 0.28 USD - go?"
2. **No names in a generator prompt:** no brand, film, franchise, director, product or real person.
3. **No user photos and no personal data go to a provider.**
4. **Never print a key.**

**Fast paths:**

- The user knows the shot: give the prompt. `shotspeak.py prompt --phrase "..."` makes 1 prompt with no options round.
- "Just give me the prompt": give the prompt. Offer a mock still after it, in 1 line.
- The user can jump back, mix parts or start again at any time. Follow them.
- The lock, the previs, the rounds and the sequence are offers. The final prompt never waits for one of them.

**Tone:**

- Plain words first, the pro term second. Teach 1 term for each option. Do not lecture.
- Ask 1 question at a time, and only when the answer changes the result.
- If the user's idea breaks a convention, say the tradeoff in 1 line and do it their way.
- Show options and images in the chat. Do not build a web page.

## The usual path

Each step is a map, not a checklist. Open the file for a step only when you do that step.

1. **Listen and interpret.** Take the words as they are. Run `plan` for 3 to 4 distinct options.
   Open [listen-interpret.md](references/flow/listen-interpret.md).
2. **Find the look, when it is not clear.** `plan` prints `UNKNOWN REFERENCE` or `LOOK NOT CLEAR`.
   Open [look-references.md](references/flow/look-references.md), then
   [look-rounds-and-lock.md](references/flow/look-rounds-and-lock.md).
3. **Mock stills.** Run `detect`, then use the route that fits. Open [mock-stills.md](references/flow/mock-stills.md).
4. **Blocking previs (optional, free).** Open [previs/index.md](references/previs/index.md).
5. **Present.** Show each option with its image and its card. Open [present.md](references/flow/present.md).
6. **Pick, mix, change.** Run `choose`. Open [choose.md](references/flow/choose.md).
7. **More than 1 shot (optional).** Run `sequence`. Open [sequences/index.md](references/sequences/index.md).
8. **De-slop mode.** The user pastes a prompt, or says a take looks fake. Open [deslop.md](references/flow/deslop.md).

## How to read these files

Read in this order, and stop when you have what the step needs:

1. This file.
2. [references/index.md](references/index.md): 1 line for each topic, with "when you need ... open ...".
3. The topic's `index.md`: 1 line for each child file, with "Read when ...".
4. The 1 child that you need. Every file is 100 lines or fewer.
5. The "See also" list at the end of a child, only when you need more.

Do not load a whole folder. A generated file says so in its first lines: change `scripts/catalog.py`, then run
`python3 SKILL_DIR/scripts/build_references.py`.

## Where to look

- [references/index.md](references/index.md): the router for the camera, the light, the words, the looks, the
  quality checks, the backends, the previs and the sequences.
- [references/commands.md](references/commands.md): every `shotspeak.py` command, its options and the exit codes.
