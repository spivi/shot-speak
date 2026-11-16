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
python3 scripts/shotspeak.py sequence --options shotspeak_out/bike-cliff/options.json --pick A --pattern build --seconds 10 --anchor "the cliff edge" --beats "he pedals hard toward the cliff edge; the front wheel leaves the edge and he flies out over the canyon; in the air he pushes the bike away from his body and the bike falls away; he drops and lands on one knee and one fist, dust bursts out; he rises slowly and looks out over the canyon" --out shotspeak_out/bike-cliff
```

Then the agent made 3 changes to the prompt block:

1. It filled the 2 `[brackets]` (`FIRST FRAME` and `LAST FRAME`).
2. It fixed the `STAGE` line for a drop: 1 cliff edge and 1 flat sandy ledge about 4 m below it.
3. It shortened the block to under 2,500 characters.

`3_skill.txt` is the final text, as sent (minus the `@Image1` lines).
