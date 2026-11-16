# Example 1, step 1: plan

```sh
python3 scripts/shotspeak.py plan \
  --phrase "the bullet time thingy where the camera swishes around them mid-air" \
  --subject "two masked ninjas" \
  --action "at the top of a jump off a low wall" \
  --setting "a walled courtyard at sunset" \
  --out examples/bullet-time
```

What the words mean in film language:

- 'Bullet time' is a frozen-moment arc: time almost stops while the camera moves.
- 'Swishy' is a fast move with motion blur: a whip pan, a fast arc or a crash zoom.
- 'Around them' is an arc shot. A partial arc is safer than a full circle.
- Air moments read best from a low camera, with a real height and real gravity.

The 4 options. Each one is a different technique family, with a different lens, light and grade:

| | Pro term | Lens | Light | Grade | Speed | The viewer feels |
|---|---|---|---|---|---|---|
| A | Frozen-moment arc (bullet time) | 35 mm | One hard low sun, camera facing into the light | Film print, deep blacks | Frozen moment | The viewer gets a held breath: one instant, seen from more than one side. |
| B | Arc shot (partial orbit, real time) | 24 mm | Low hard side sun | Warm natural | Real time | Energy and swagger. The camera has an attitude of its own. |
| C | Speed ramp | 50 mm | Low hard side sun | Cool and desaturated | Speed ramp | The viewer feels the speed and then gets a clear look at the best instant. |
| D | Low-angle wide shot | 18 mm | Silhouette with a rim | Bleach bypass | Slow motion (one beat) | Scale and power. The subject is bigger than the viewer. |

Recommended: **A**. It is the closest match to your words. Best for: one peak moment in the whole piece: the top of a jump, the instant before a landing or a hit.

The script also printed:

```text
Note: Options A, D slow time down. In a finished piece, use slow motion for 1 beat only.
Anti-slop check: passed for every option.
```

The complete cards, with the diagrams and the prompts, are in [`bullet-time/options.md`](../bullet-time/options.md).

## See also

- [Example 1: the steps](index.md): the user's words and the other steps
- Next: [Step 2: the card for option A, as shown in chat](2-card.md)
