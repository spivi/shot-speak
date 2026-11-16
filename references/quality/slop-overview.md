# AI-slop avoidance

Read this file before you write or approve any option, image prompt or video prompt.

"AI slop" is the look a generator returns when the prompt makes no decisions. Each default below is a tell.
A viewer who sees 2 or 3 tells together stops believing the picture.

The rule behind every fix: **a generator fills each gap with its default. Close the gap with a decision.**
Decide the camera position, the lens, the light source and the speed. Then forbid the default in plain words.

The same tells are data in `scripts/catalog.py` (`SLOP_TELLS`). The scripts use them 3 ways:

- `plan`, `mock`, `choose` and `prompt` run the anti-slop check on every option. A finding is advice. It never blocks a request.
- The prompt builder adds an `AVOID:` clause for each relevant tell to the image prompt and the video prompt.
  It drops a clause that the user's own subject, action or place asks for, so that a prompt never contradicts the user.
- `deslop` flags the tells in a prompt that the user wrote, and prints a rewrite. A clean prompt comes back unchanged.

## The anti-slop check

Run this check on every option before any image is made. `scripts/shotspeak.py plan` runs the mechanical part.
Do the judgement part yourself.

1. **Camera:** The height, the side and the distance are stated. The subject is not centred and not frontal.
2. **Eyes:** Every eyeline has a target inside the scene. No face turns to the lens.
3. **Lens:** A focal length is stated with a reason. A 35 to 50 mm lens at chest or eye height has a stated reason and an off-axis position.
4. **Light:** 1 named source with a direction. A share of the frame is in true shadow. No glow, bloom, haze, fog or wet floor.
5. **Speed:** Real time, or 1 named slow beat. No drift. Each camera move has a start and an end.
6. **Arc:** Any arc is less than 180 degrees and stays on 1 side of the action.
7. **Finish:** A grade that was selected, not the default. Worn textures. No quality words.
8. **Set:** The 3 to 4 options do not share the same light, the same lens and the same camera height.

If the user's idea breaks a rule on purpose, say the tradeoff in 1 line and do it their way.
On each option card, write 1 or 2 lines: which tells this option avoids.

## When a tell is a choice

A tell is a default that nobody chose. The same technique, chosen, is craft. The check keeps a tell when the user's
words make it a choice: the place or the story names it ("a foggy harbour"), or the sentence says "on purpose",
"deliberately" or "intentionally". In `options.json`, an option can list tell ids in `on_purpose`.
The check reads words only. It does not understand the scene. A kept tell shows the words that kept it.
A prompt that asks for a tell and also forbids it gets a note: the prompt contradicts itself.

| The tell | Fine when |
|---|---|
| Centred, front-facing subject | a planned symmetry, a product shot, an interview or a direct address to the viewer |
| Eyes into the lens | a direct address, an interview, a vlog or a fourth-wall break |
| Eye-level medium shot as the default | dialogue and interviews, where a neutral height is the point |
| Symmetrical hero framing | a planned one-point perspective, a tableau or a poster frame |
| 180 or 360 degree orbit | a product on a turntable, or a planned reveal with no face in the path of the camera |
| No camera position stated | a reference frame or a previs gives the camera position |
| Soft, even golden glow | a named soft source (a window, a grey sky), a high-key comedy or product look, a dream or storybook style |
| Bloom, haze, fog and god rays | fog, mist, smoke or steam is part of the place or the story ('a foggy harbour at dawn') |
| Glossy wet floors | rain or water is part of the story |
| Lens flare everywhere | the light source itself is in the frame, or an anamorphic look is a choice |
| No light source stated | a reference frame gives the light, or the style is flat 2D |
| The 35 to 50 mm default | a normal lens chosen on purpose, when the move or the place carries the feeling |
| Fake creamy bokeh, or everything in focus | a long lens or a macro lens makes the blur: state the lens and what is sharp |
| No lens stated | a reference gives the lens, or the style has no lens (2D animation) |
| Aquarium speed: slow floating camera and slow bodies | a dream, underwater or zero-gravity scene, or a calm piece that wants a slow drift |
| Slow motion everywhere | a high-speed product, liquid or dream piece where slow is the whole idea |
| Floating, weightless bodies | water, space, magic, or a light object (a feather, seeds, a balloon) really floats |
| No speed stated | a reference gives the speed, or a frame rate is stated |
| Over-saturated HDR look | vivid colour in a cartoon, a toy or a pop style. Quality words (4k, 8k, masterpiece) never help |
| Perfect, clean textures | a product, a toy, an animation or a new object that must look new |
| Teal and orange by default | a deliberate blockbuster look |
| 'Cinematic' and 'epic' with no direction | never needed: the camera, the lens, the light and the speed say it |

## See also

- [Camera and light tells](slop-camera-light.md): you check composition or light
- [Lens, motion and finish tells](slop-lens-motion-finish.md): you check the lens, the speed or the grade
- [Avoid clauses](avoid-clauses.md): you write a prompt by hand
- [De-slop mode](../flow/deslop.md): the user brings a prompt or a take
