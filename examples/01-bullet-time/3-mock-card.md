# Example 1, step 3: the mock card (dry run)

```sh
python3 scripts/shotspeak.py mock --options examples/bullet-time/options.json --backend openai --dry-run
```

The dry run prints the 4 image prompts, then the cost card. Nothing is sent. The prompt for option A:

```text
A single still frame from a live-action film, 16:9 frame. A storyboard-grade production mock that shows framing, lens, light and colour.
SUBJECT: two masked ninjas at the top of a jump off a low wall, in a walled courtyard at sunset. Generic stand-in figures, not a likeness of any real person.
CAMERA: the camera is at the middle of its arc, exactly side-on: the subject in clean profile at their own height. Camera placement: at the subject's own height, the lens level, 2 to 3 m away, on one side of the action for the whole move.
LENS: 35 mm; moderately wide lens look: subject and surroundings both readable, natural perspective.
LIGHT: one hard low sun as the only strong light, behind the subject; the camera faces into the light; bright rims on hair and shoulders, long shadows that fall toward the lens, about a third of the frame in deep true shadow.
COLOUR: photochemical film look: fine grain, deep true blacks with detail, natural skin and material colours, restrained saturation.
MOMENT: everything caught perfectly sharp at one instant: dust and small debris hang still in the air.
FACES: turned away from the lens, in profile, three-quarter or from behind.
AVOID: the camera never completes a half circle and never reaches a view straight in front of the face; real gravity and real jump height, nobody floats; nobody looks into the lens; every eyeline goes to a target inside the scene; no soft even glow; one motivated light source with a real dark side; no bloom, no haze, no fog, no volumetric god rays; matte worn floor, no glossy or wet reflections; worn real textures with dust, creases and small defects, nothing plastic or perfectly clean; no over-saturated HDR look; restrained colour and true blacks; no lens flare unless the light source itself is in the frame.
One frame only: no collage, no split screen, no text, no captions, no logos, no watermark, no border.
```

The end of the card (the fingerprint is the value for `--confirm`):

```text
Backend:   openai  (model gpt-image-2.5-flare)
Size:      1536x864   Quality: medium
Images:    4
Estimate:  0.28 USD
Card:      <fingerprint>
```

The agent shows the count and the estimate, and waits for a clear yes.

## See also

- [Example 1: the steps](index.md): the user's words and the other steps
- Next: [Step 4: choose](4-choose.md)
