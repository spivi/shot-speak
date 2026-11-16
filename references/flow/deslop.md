# De-slop mode

Read this file when the user pastes a prompt, or says that a take looks fake, generic or "AI".

```sh
python3 SKILL_DIR/scripts/shotspeak.py deslop --text "THE PROMPT"
```

Show the tells in groups with 1 line of reason each. Rewrite the prompt from the script's rewrite, and replace
each `[bracket]` with a decision. A `[kept]` line is a technique that the user chose. Do not change it. Run `deslop` on your rewrite until it finds no tell. List the changes in
plain words. For a take that the user describes without a prompt, use the table "The user says / Probable
tell / First fix" below.

## De-slop mode: fix a prompt or a take that the user brings

Use this mode when the user pastes a prompt, or describes a take that "looks AI".

For a pasted prompt:

1. Run `python3 scripts/shotspeak.py deslop --text "PROMPT"` (or `--file PATH`).
2. Show the tells in groups: composition, lighting, lens, motion, finish. For each tell, give the reason in 1 line.
3. Rewrite the prompt yourself. Start from the script's rewrite. Replace each `[bracket]` with a decision.
   If a decision changes the meaning of the shot, ask the user. Offer 2 choices with a recommendation.
4. Run `deslop` on your rewrite. Repeat until the script finds no tell.
5. Show the old prompt and the new prompt, and list the changes in plain words.

For a described take ("the camera floats", "it looks like a game", "everyone is glowing"):

1. Map each complaint to a tell in the tables above.
2. Ask for the prompt. If the direction is absent from the prompt, add the direction.
3. If the direction is present and the generator did not follow it, say so. Then simplify the shot:
   1 move, 1 light source, fewer people, a shorter length.

| The user says | Probable tell | First fix |
|---|---|---|
| "It looks like a video game" | Everything in focus, perfect textures, HDR colour | Capture look: grain, true blacks, worn textures, a stated lens |
| "The camera floats" / "it is too slow" | Aquarium speed | Locked frame or 1 fast move, real-time action, cut on movement |
| "They look at me" | Eyes into the lens, frontal framing | Side-on or three-quarter position, an eyeline target in the scene |
| "It glows" / "it is milky" | Soft glow, bloom, haze | 1 hard source, one third of the frame in shadow, clear air |
| "It looks like an advert" | Centred hero framing, front light, clean textures | Off-centre subject, backlight, wear |
| "They fly" | Floating bodies, slow motion | Real height, real gravity, low camera, cut at the top |
| "It all looks the same" | Default lens and height in every shot | Alternate 18 mm low and 85 to 135 mm far |

The script finds words. It does not see pictures and it does not understand a scene. A prompt with no tell
can still give a dull frame. The check is a floor, not a judgement of quality.

## See also

- [The slop guide](../quality/index.md): the tells, the check and the avoid clauses
- [Avoid clauses](../quality/avoid-clauses.md): the exact words for a rewrite
