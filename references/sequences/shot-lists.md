# Sequences: shot lists

Read this file when the user wants more than 1 shot: the command, the patterns and the rules for a shot list.

## The short version

For a fight, a hit, a chase or a small scene:

```sh
python3 SKILL_DIR/scripts/shotspeak.py sequence --options PATH --pick B --pattern impact --seconds 10
```

It writes a shot list with exact cut times around the picked option.

## When 1 shot is not enough

A single camera move cannot show a whole action. Energy comes from cutting. Many video tools can make
several short shots in 1 clip when the prompt gives a shot list with exact cut times.

| The user says | Offer |
|---|---|
| "show the whole thing", "a little scene" | `--pattern coverage` |
| "I want to feel the hit", a punch, a catch, a landing, a crash | `--pattern impact` |
| "it builds up", "then the big moment" | `--pattern build` |

```sh
python3 SKILL_DIR/scripts/shotspeak.py sequence --options shotspeak_out/NAME/options.json --pick B \
  --pattern impact --seconds 10 --anchor "the blue door" \
  --beats "both still; the right fist starts; the fist stops on the jaw; the head turns, he steps back; both still"
```

The picked option becomes the hero shot. The script calculates the cut times. They add up to the clip length.
A shot is 1 second or longer. Without `--beats`, the prompt has `[brackets]`. Replace each bracket with a decision.
Read the length limit of the user's video tool before you select `--seconds`.

## Rules for a shot list

1. **One action and one camera move in each shot.** Two moves in 1 shot give a soft, drifting result.
2. **State the number of shots, the number of cuts and each cut time.** "5 shots joined by 4 hard cuts at exactly 1.5, 4, 6, 8 s."
3. **The cut comes when the motion ends.** For a hit, cut at the end of the reaction. A cut in a still moment is visible.
4. **One lens for each shot type.** Example: 24 mm for the place, 35 mm for whole bodies, 50 mm for a medium shot, 85 mm for inserts.
5. **One speed rule for the whole clip.** Example: "real time in every shot, slow motion only on the approach of the contact insert".
6. **One light direction and one grade for the whole clip.**
7. **A small stage.** Keep the whole action within 2 m of 1 anchor object. A large place with 2 sides confuses a generator.
8. **One side of the action.** Draw a line through the 2 people, or along the direction of travel. The camera stays on 1 side of that line in every shot. Then left stays left.
9. **Each person keeps 1 screen side.** State it: "the taller one on screen left".
10. **Eyes on a target inside the scene.** Nobody looks into the lens.
11. **State the first frame and the last frame.** Positions, what each person holds, the light. Hold the last frame still.

## See also

- [Contacts and groups](contact-and-groups.md): the shot has a hit or several people
- [Speed guide](../camera/speed.md): you set the speed rule
