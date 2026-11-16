# Bike over a cliff: 3 prompts, 3 real videos

The idea, in the words of the user:

> 10 seconds of a cool action scene: a guy rides a bike over a cliff, ditches the bike mid-air and does a superhero landing

The 3 videos are in [`docs/video/bike-cliff/`](../../docs/video/bike-cliff/). The file
[`receipts.json`](../../docs/video/bike-cliff/receipts.json) holds the hash of each file and each prompt.

| File | Prompt | Video |
|---|---|---|
| [`1_noob.txt`](1_noob.txt) | The first prompt, as most people type it | `1_noob.mp4` |
| [`2_plain.txt`](2_plain.txt) | A clear prompt, no film language | `2_plain.mp4` |
| [`3_skill.txt`](3_skill.txt) | The prompt block that shot-speak wrote | `3_skill.mp4` |

Each request used the same model (Seedance 2.5 reference-to-video), 480p, 10 s and 1 take.
1 face reference of the author was attached to all 3 requests, with the author's consent.
The files here do not hold the `@Image1` lines. The sent text had these 3 additions:

- `1_noob.txt` started with "@Image1 is me."
- `2_plain.txt` started with "The man in @Image1 is the rider."
- `3_skill.txt` had 1 `REFERENCE:` line (use `@Image1` for the face, hair and beard only) and named `@Image1` in `SUBJECT:`.

## How the third prompt was made

The 2 commands wrote [`options.md`](options.md) and [`sequence.md`](sequence.md):

```bash
python3 scripts/shotspeak.py plan --phrase "10 seconds of a cool action scene: a guy rides a bike over a cliff, ditches the bike mid-air and does a superhero landing" --subject "a young man in a grey hoodie and jeans" --action "rides a mountain bike off a cliff edge, lets go of the bike in mid-air and lands on the ground below in a superhero landing" --setting "a rocky desert canyon at late afternoon" --out shotspeak_out/bike-cliff
python3 scripts/shotspeak.py sequence --options shotspeak_out/bike-cliff/options.json --pick A --pattern build --seconds 10 --anchor "the cliff edge" --beats "he pedals hard toward the cliff edge; the front wheel leaves the edge and he flies out over the drop; in the air he pushes the bike away from his body and the bike falls away; he drops from the top of the wall and lands in a clean superhero landing, dust bursts out; he rises slowly into a confident stand and looks up at the cliff edge he jumped from" --out shotspeak_out/bike-cliff
```

Then the agent made these changes to the prompt block:

1. It filled the 2 `[brackets]` (`FIRST FRAME` and `LAST FRAME`).
2. It fixed the `STAGE` line for a drop: 1 cliff edge on top of a 4 m rock wall, and the flat sandy canyon floor
   at the foot of the wall. He lands on the floor, and nothing drops away behind him.
3. It took the colour grade of option C (warm natural) in place of the bleach bypass of option A, as the
   `choose --mix grade=C` command does. It wrote the grade as a warm red-rock palette.
4. It wrote the landing of shot 4 as a controlled superhero landing, and shot 5 as a medium shot from three-quarter
   front, so that his face is visible as he rises.
5. It added 2 clauses to `AVOID` for the landing and for the face in shot 5, and it added `no black-and-white or
   washed-out colour`.
6. It shortened the block to fit the prompt limit of the model.

`options.md` and `sequence.md` show the plan as the commands wrote it, with the beats of the final prompt.
`3_skill.txt` is the final text, as sent (minus the `@Image1` lines). The README at the top of the repository
takes the shot list from `3_skill.txt`.

In the video, the model cut at 1.67, 3.67, 4.88 and 7.92 s (measured), not at the 2.5, 4.5, 5.5 and 8.5 s of the prompt.
