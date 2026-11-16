# Sequences: chains, drafts and selection

Read this file when a scene runs across several clips, or when you plan the drafts.

## Chains: a scene longer than 1 clip

- Use the last frame of clip 1 as the start frame of clip 2, when the tool accepts a start frame.
- In the prompt of clip 2, state the last frame of clip 1 again: positions, grip, light, wardrobe, damage.
- Use an end frame to force a landing or an end position.
- If 1 part of a clip is wrong, generate only those seconds again and join them in the edit.
- Hide a join on movement. A whip pan gives a cut point that the viewer does not see.

## Drafts and selection

- Make drafts at the lowest resolution of the tool. Check positions and framing only.
- A higher-resolution run of the same prompt is a new result. It can differ. Check it again.
- For action, 2 to 4 takes of the same prompt give different moments. Select by moment, not by whole take. Tell the user the cost of the batch first.
- After a take, send exact fixes. Use 3 fixes at most in 1 pass.
- Build 1 scene in the edit from the best moments of several takes.

## See also

- [Blocking and references](blocking-and-references.md): you attach a reference
- [Backends: cost](../backends/cost-and-limits.md): a batch of takes costs money
