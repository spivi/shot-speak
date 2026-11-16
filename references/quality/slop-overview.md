# AI-slop avoidance

Read this file before you write or approve any option, image prompt or video prompt.

"AI slop" is the look a generator returns when the prompt makes no decisions. Each default below is a tell.
A viewer who sees 2 or 3 tells together stops believing the picture.

The rule behind every fix: **a generator fills each gap with its default. Close the gap with a decision.**
Decide the camera position, the lens, the light source and the speed. Then forbid the default in plain words.

The same tells are data in `scripts/catalog.py` (`SLOP_TELLS`). The scripts use them 3 ways:

- `plan` and `mock` run the anti-slop check on every option. A finding blocks image generation.
- The prompt builder adds an `AVOID:` clause for each relevant tell to the image prompt and the video prompt.
- `deslop` flags the tells in a prompt that the user wrote, and prints a rewrite.

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

An option that fails goes back to step 3 of the workflow. Do not generate an image for it.
On each option card, write 1 or 2 lines: which tells this option avoids.

## See also

- [Camera and light tells](slop-camera-light.md): you check composition or light
- [Lens, motion and finish tells](slop-lens-motion-finish.md): you check the lens, the speed or the grade
- [Avoid clauses](avoid-clauses.md): you write a prompt by hand
- [De-slop mode](../flow/deslop.md): the user brings a prompt or a take
