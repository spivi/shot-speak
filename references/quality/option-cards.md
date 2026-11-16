# Option cards and the final spec

Read this file when you present options or the final shot spec in chat.

## The option set

- Give 3 or 4 options. 4 is the default.
- **Make the options different ideas.** Change the technique family, and with it the camera height, the lens
  and the light. 4 arcs at 4 speeds is 1 idea, not 4.
- Mark exactly 1 option as recommended. Give the reason in 1 sentence that uses the user's own words.
- Run the anti-slop check ([the slop guide](slop-overview.md)) before any image exists. Fix each finding, or keep
  it when it is the user's choice.
- If more than 1 option slows time down, say that a finished piece uses slow motion for 1 beat only.

## The card

Show each option in chat in this order. Keep each line short. Use plain words first and the pro term second.

```text
Option B: <pro term>            (recommended, when it is)
[mock image, or the text diagram when there is no image]

In plain words:        1 sentence
What the viewer feels: 1 sentence
Pro term to learn:     the term, so the user can search for examples
Choose it when:        1 sentence

Camera movement:   ...
Camera placement:  height, side, distance, tilt
Lens:              focal length + why
Light:             setup + the source and what stays dark
Colour grade:      ...
Speed:             real time / slow motion / speed ramp / frozen moment
Length:            ...

AI look it avoids:  1 or 2 slop tells
Risks with AI video generators: 2 or 3 bullets, each with the words that reduce the risk
Say this to a video model: 1 line, no model names, no brand names
```

`scripts/shotspeak.py plan` writes this card for each option to `options.md`. Show the cards in the
conversation. Do not send the user to a file to read them, and do not build a web page.

## Text-only diagrams

With no image backend, each card carries 2 text diagrams from the script:

- **Top view:** `S` is the subject with an arrow for the direction. `C` is the camera, with its path. The light
  direction is marked when it matters.
- **Frame sketch:** a 16:9 box that shows where the subject sits and what fills the frame.

Add the copy-ready mock image prompt under the diagrams. Tell the user that any image tool can take it.

## After the cards

Ask 1 question: "Pick 1, mix parts, or do you want other options?" Then:

- **Pick:** `choose --pick B`.
- **Mix:** the lens, the light, the grade and the speed can come from another option:
  `choose --pick A --mix light=C --mix lens=D`. The camera movement and placement stay with the picked option.
  Check that the mix makes sense. A frozen-moment arc with flat overcast light loses its rims.
- **Other options:** read [the camera moves](../camera/moves/index.md), select 3 to 4 other techniques from other families, and run
  `plan --techniques id1,id2,id3,id4`. Do not repeat a rejected option with a small change.
- **A custom option:** edit `options.json` by hand. Keep every field. Run `mock --options PATH --dry-run`:
  it validates the set and runs the anti-slop check again.

## The final spec

`choose` writes `choice.json` and `final_spec.md`. Show the user:

1. The decision table: movement, placement, lens, light, grade, speed, length.
2. "Watch for": the generator risks of the final shot.
3. The prompt block, in a code block, ready to copy.
4. The 1-line version.

The prompt block has fixed headings:

```text
SHOT: / SUBJECT AND ACTION: / CAMERA MOVE: / CAMERA PLACEMENT: / LENS: / LIGHT: / COLOUR: / SPEED: / RULES: / AVOID:
```

Before you hand it over:

- Replace the stand-in subject with the user's real subject **in words the user gave**. No real names.
- State the exact number of people and each person's screen side.
- Add the user's action in visible terms: what moves, where it ends.
- Keep the prompt free of model names, brand names and film titles.
- Tell the user that the mock image is for framing and light only, not a face reference.

## See also

- [Pitfalls](pitfalls.md): you write risks or the final prompt
- [Camera moves](../camera/moves/index.md): you select other techniques
