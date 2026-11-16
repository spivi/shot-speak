# Changelog

## Unreleased

### Medium-aware prompts, provider status checks and approval of the estimate

- **The medium follows the user's words.** Live action stays the default, with the same prompts as before. Words such
  as "stop-motion", "3D animated", "cartoon" or "watercolour illustration" select that medium: the mock still names
  it, and the prompts use its words (believable weight, handmade or drawn textures, no film grain for drawn or
  rendered work). `plan` says the medium in 1 line; `medium` in `options.json` changes it. There is no new question,
  flag or step.
- **A contradiction is checked in its own shot.** "No slow motion except at the peak" forbids nothing whole, and a
  negation in another shot does not contradict this one. A forbid in a line for every shot (an `AVOID:` line) still counts.
- **The card fingerprint covers the estimate.** The number of images and the estimated total are part of the yes, so a
  changed estimate needs a new yes. The fingerprints in the examples and the README changed for this reason.
- **Provider status checks.** A Replicate status link is opened only on the https host of the request, with at most
  60 checks or 300 s. A redirect gets the key only on the same host, and only https redirects are followed.
- `README.md`: the quick start, the caps, the fingerprint and the craft lines describe the current behaviour.

### Correctness, spend safety and context-aware anti-slop

- **The decisions are the source of truth.** The image prompt and the video prompt of an option are rebuilt from its
  decisions on each run, so an edit of the lens, the move, the placement, the light, the grade, the speed or the
  subject can no longer leave a stale prompt. `options.json` records what each prompt was built from
  (`prompt_basis`). A prompt that you edit by hand is kept while its decisions stay the same; a hand edit whose
  decisions changed later is refused with the fix. A round, a mix or an edit that changes the placement, the lens or
  the speed removes the old words from the technique's wording and states the new decision.
- **Image cache by content.** An image is reused only when its receipt names the exact request (backend, model, size,
  quality, prompt, extra fields) and the file still has the receipt's hash. A file with no receipt is requested
  again. `receipts.json` keeps the latest receipt of each option and is written after each request.
- **Request integrity.** `SHOTSPEAK_<NAME>_EXTRA_INPUT` can no longer replace the prompt or ask for more images, and
  cannot carry a link, a file path or a name. The card fingerprint covers the extra fields. With no extra fields the
  fingerprint is the same as in 0.2.0. A model id cannot change the endpoint path.
- **Provider answers are checked.** Only 1 complete PNG, JPEG or WebP image is saved, under the extension of its real
  format, in 1 atomic write. An empty, cut-off, malformed or oversized answer, invalid base64 or a non-https image link
  is an ambiguous failure, and nothing is saved.
- **Anti-slop is advice, and it reads context.** A finding never blocks a request; the 4 hard gates are unchanged.
  A negation covers only the rest of its clause, so "a man who never smiles, camera orbiting around him" is flagged
  and "No fog, no haze" is never rewritten. A prompt that asks for a tell and forbids it is flagged as a contradiction.
  A technique that the user's words make a choice (fog in the place, an interview, stop-motion, a product turntable,
  "on purpose") is kept and shown as kept. Every tell has a "Fine when" note.
- **De-slop is proportional.** A clean prompt comes back unchanged. The Avoid line holds only clauses for what was
  removed or left undecided, and a second run changes nothing more.
- **The builder follows the user's words.** A subject, an action or a place that asks for a technique (a foggy harbour,
  a look into the lens) no longer gets an avoid clause that forbids it.
- `README.md`: the install command has the real clone URL. New `docs/evaluation.md`: an offline evaluation set
  (`tests/fixtures/prompt_cases.json`) and a protocol for a blind human review of takes.
- `tests/test_release.py` checks the files that Git can commit, so a local tool cache no longer fails the gate.

Small files with indexes. Every guide file is 100 lines or fewer, so an agent loads only what the step needs.

- `SKILL.md` is 72 lines: the Spirit, the 4 hard gates, the usual path (1 line a step, each names its file) and
  "How to read these files": `SKILL.md`, then `references/index.md`, then 1 topic `index.md`, then 1 child, then
  its "See also" list when it needs more.
- `references/` is now a tree of topics, each with an `index.md` (1 line for each child: a link and "Read when ..."):
  `flow/` (the steps and de-slop mode), `camera/` (moves, placement, lens, speed), `light-colour/`, `language/`,
  `looks/`, `quality/` (the slop tells in 4 files, avoid clauses, pitfalls, option cards), `backends/` (by route),
  `previs/` and `sequences/`. `references/commands.md` holds the command table that was in `SKILL.md`.
  The wording of the guides did not change. Files were split, retitled and linked.
- `scripts/build_references.py` writes the generated files at the new paths: `camera/moves/` (7 files, by
  technique group), `language/phrase-map.md` and `looks/` (7 files, by genre). It splits a group that grows past
  100 lines. `--check` also fails when a generated file from an old layout is left over. Without `--check` the
  script removes such a file.
- `examples/01-bullet-time.md` is now `examples/01-bullet-time/` (an index and 1 file for each step).
  `examples/index.md` lists the examples.
- `README.md` is about half as long (966 to 448 lines). The repeated sections are merged or cut: the full prompts and the previs show for the
  first example only (the others link their folder), the walkthrough steps no longer repeat example 1, the separate
  "Demo", "Example session", "Cost", "Privacy", "Comparison images" and "Tests" sections are gone, and "Image backends",
  "Cost" and "Privacy" are 1 section. The detail moved to `references/backends/`. `build_walkthrough.py` writes the shorter blocks.
- New `tests/test_docs.py`: every guide file has 100 lines or fewer, every relative link resolves, every reference
  file is reachable from `SKILL.md`, and every `index.md` links each file and each child index in its folder.

## 0.2.0 - 2026-11-15

The skill became an enabler with more craft in it. All new stages are optional. The mock stills and the final
prompt never wait for one of them.

Spirit

- `SKILL.md` starts with a "Spirit" section: 4 hard gates (a clear yes before money is spent, no names in a
  generator prompt, no personal data to a provider, no printed keys), fast paths, and 1 question at a time.
  Every other step is guidance that the agent can skip, reorder or shorten.
- `prompt`: the fast path. 1 final prompt for a phrase, with no options round.
- The cost confirmation is a 1-line question. `mock --dry-run` prints it.

Blocking previs (optional, free, local)

- `blender-detect`: finds a local Blender (the `BLENDER` variable, PATH, the standard folders), its version,
  and a live Blender MCP add-on socket. It reports 1 route: `mcp`, `headless` or `none`. It opens no window.
- `previs`: for each option, a grey-box scene with a 1 m floor grid, set boxes from the words of the place,
  faceless mannequins with the correct count, screen sides and facing, and a camera whose focal length,
  height, distance, side and move come from the words of the option. Output: 3 camera stills, an overhead
  plan with the camera path, a short animatic, the `.blend` file and `previs/previs.json` with SHA-256 values.
- The same `options.json` gives the same Blender script, byte for byte. Handheld noise is seeded.
- An animal gets a four-legged stand-in. A thrown object (a bone, a ball, a disc, a stick) flies in on a real
  curve of gravity and arrives at the mouth or the hands on the middle frame.
- Pure-geometry framing checks without Blender: screen side, shot size, a head outside the frame, a face to
  the lens, a camera that crosses the action line. A line-of-sight check runs in Blender.
- Route `none` skips the stage, says why and exits with 0.
- `choose` lists the previs files in the final spec. `choose --layout-ref` adds a layout-reference line.

Craft

- Look recipes ("like that film"): 34 named looks as decisions. `plan` recognises a film, a director, a genre
  or an era, makes the recipe option A and removes the name. The names are in `scripts/look_aliases.json`
  only. The name check now also blocks every look name. `looks` lists and searches the recipes.
- When the look is not clear: a deterministic vagueness test in `plan`; `refs` prints search links for
  public reference sites and opens nothing; `round` makes a round of 2 to 4 mock stills that differ in 1
  decision, with a running total, rejected values that do not come back, and a cap of 3 rounds that the user
  can raise; `lock` writes `look_lock.json`. `choose` shows `LOCKED`, `UNLOCKED` or `LOCK IS STALE`, and works in all 3 cases.
- `sequence`: several short shots in 1 generation with exact cut times. 3 patterns: `coverage`, `impact`, `build`.
- New technique `impact_insert` (contact insert) and new speed `ramp_on_contact`. New phrase rules for
  hits, catches and landings, and for "push in". 25 techniques, 6 speeds, 28 phrase rules.
- The place names the light: "at night", "sunset", "candles" or "a grey day" select a light that fits.
- 4 new guides: `look-recipes.md` (generated), `finding-the-look.md`, `sequences-and-action.md`, `blocking-previs.md`.

Image backends

- Order: OpenAI, Higgsfield (`HF_KEY`), then fal.ai and Replicate as extras. The Higgsfield route follows the
  provider's client (1 submit, status checks on the link of that request). It is not verified with a live
  request, and its cost is "unknown" to the tool. It moves to the top after 1 live image request confirms it.
- `detect --image-tool NAME` and `detect --no-image-tool` print the next step for the agent's case: Codex
  with the built-in `image_gen` tool, or an agent with no image tool.
- `mock --import option_B=FILE` registers an image that the user made with a pasted prompt.

Documentation

- The README starts with the dog. It has 4 scenes with 3 prompts each (the first prompt, a clear prompt with
  no film language, the shot-speak result), a step-by-step walkthrough, and a "Further reading" list.
  `scripts/build_walkthrough.py` writes those sections from the committed example outputs.
- `docs/replay.svg`: an animated replay of 1 session. CSS animation only, no script.
- `docs/walkthrough/index.html`: an interactive page with no outside files.
- `scripts/build_images.py` makes the 16 comparison images after a yes. The image slots hold grey placeholders.
- 7 example folders with command transcripts. 60 previs stills from Blender 5.2.2.

Tests: 133 offline tests. 1 integration test runs Blender without a window and skips when there is no Blender.

Not yet verified: every network path, the Higgsfield image endpoint and its input fields, the Blender MCP
route, Blender versions other than 5.2, and the previs on Linux and Windows.

## 0.1.0 - 2026-11-14

First version.

- `plan`: plain words to 3 or 4 distinct shot options. 26 phrase rules, 24 techniques, 11 lighting setups,
  9 colour grades, 5 speeds. The same input gives the same output.
- Anti-slop check on every option before an image is made. 22 AI-slop tells in 5 groups: composition,
  lighting, lens, motion, finish.
- The prompt builder adds avoid clauses for the relevant tells to each image prompt and video prompt.
- `deslop`: flags the AI-slop tells in a pasted prompt and prints a rewrite.
- `mock`: mock stills through the OpenAI Images API, fal.ai or Replicate, with a dry run, a cost estimate,
  a card fingerprint for confirmation, an image cap and a cost limit. Host mode for a built-in image tool.
  Text-only mode with top-view and frame diagrams.
- `choose`: pick or mix options, then a final shot spec and a model-agnostic prompt block.
- `detect`: backend detection that never prints a key.
- 11 reference guides. 2 of them are generated from the catalogue by `scripts/build_references.py`.
- 2 worked examples, rebuilt from real script output by `scripts/build_examples.py`.
- 69 offline unit tests. A test fails if any test tries to reach the network. Tested on Python 3.9, 3.12 and 3.14.

Not yet verified with a live request: every network path. See "Limitations" in the README.
