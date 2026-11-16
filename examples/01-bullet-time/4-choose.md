# Example 1, step 4: choose

The user says: "A, but with the harsh silvery look of D."

```sh
python3 scripts/shotspeak.py choose --options examples/bullet-time/options.json --pick A --mix grade=D
```

The final prompt block ([`bullet-time/final_spec.md`](../bullet-time/final_spec.md)):

```text
SHOT: Frozen-moment arc (bullet time). 16:9 frame, 2 to 3 s.
SUBJECT AND ACTION: two masked ninjas at the top of a jump off a low wall, in a walled courtyard at sunset.
CAMERA MOVE: a fast, smooth arc of about 130 degrees around the subject: it starts behind the shoulder, passes the profile and stops at a front three-quarter view; it never reaches a view straight in front.
CAMERA PLACEMENT: at the subject's own height, the lens level, 2 to 3 m away, on one side of the action for the whole move.
LENS: 35 mm.
LIGHT: one hard low sun as the only strong light, behind the subject; the camera faces into the light; bright rims on hair and shoulders, long shadows that fall toward the lens, about a third of the frame in deep true shadow.
COLOUR: bleach-bypass look: high contrast, low saturation, silvery highlights, dense blacks, visible grain.
SPEED: time almost stops: the subject drifts only a hand's width while the camera moves fast; real gravity returns at the end of the move.
RULES: State the exact number of people. Screen direction stays the same for the whole shot.
AVOID: the camera never completes a half circle and never reaches a view straight in front of the face; real gravity and real jump height, nobody floats; nobody looks into the lens; every eyeline goes to a target inside the scene; no slow floating camera drift; the camera is locked or makes one decisive move with a clear end; no bloom, no haze, no fog, no volumetric god rays; no soft even glow; one motivated light source with a real dark side; worn real textures with dust, creases and small defects, nothing plastic or perfectly clean.
```

Before the user pastes it into a video generator, the agent adds what only the user knows: "exactly 2 people",
which ninja is on screen-left, and what each one wears.

## See also

- [Example 1: the steps](index.md): the user's words and the other steps
- Next: [Example 2: de-slop a prompt](../02-deslop.md)
