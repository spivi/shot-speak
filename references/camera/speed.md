# Speed guide

Read this file when you select or explain the speed of a shot.

## Speeds

The key in code format is the value used in `scripts/catalog.py`.

| Speed | Plain words | Use it for | Prompt wording |
|---|---|---|---|
| `real_time` Real time | Normal speed. Fast things are fast. | Almost everything | "real time for the whole shot, fast and crisp, no slow motion" |
| `slow_motion` Slow motion (one beat) | The moment is stretched. | 1 moment in the whole piece | "slow motion for this one beat only; real gravity, nothing floats" |
| `speed_ramp` Speed ramp | Normal, a short slow-down at the peak, then normal. | A jump, a trick, a throw, a hit | "real time into the move, a short ramp to slow motion at the peak, then back to real time" |
| `frozen_moment` Frozen moment | Time almost stops while the camera moves. | The 1 peak instant ("bullet time") | "time almost stops: the subject drifts only a hand's width while the camera moves fast" |
| `fast_cutting` Real time, fast cutting | Many short shots at normal speed. | Showcase, introduction, trailer energy | "short shots of about 1 second, a hard cut on each movement" |
| `ramp_on_contact` Ramp on contact | Slow on the way in. Full speed from the contact. | 1 decisive contact: a hit, a catch, a landing | "slow motion on the approach, then real speed from the exact frame of contact" |

## Rules

- **Real time is the rule.** Generated video drifts toward slow, even motion. Write the speed in every prompt.
- **Slow motion once.** Select the 1 moment in the piece that earns it. Everything else is real time.
- **Say where the slow part starts and ends.** "Slow motion on the approach, real speed from the frame of contact."
- **Speed comes from cutting, not from fast playback.** Use many short shots and change the camera mode in each one.
- **Write the stillness.** Fast action reads when a still moment comes before it and after it.
- **Remove the wind-up.** "The first visible motion is the action itself."
- **Real gravity.** With slow motion or a frozen moment, write a real height and "nothing floats".
- **A frozen moment ends.** Write "at the end of the move, time runs again".
- **A whip pan is a cut point.** The blur hides the join between 2 clips.
- **Cut on movement or on the impact.** A cut in a still moment is visible.
- **Calculate shot times.** In a prompt with several shots, the shot lengths must add up to the clip length.
- A push-in of less than 1 second is hard to see. Give a camera move at least 1.5 seconds, or lock the camera.

## See also

- [Camera moves](moves/index.md): you need a technique's default speed
- [Sequences: shot lists](../sequences/shot-lists.md): the clip has several shots
- [Slop tells: lens and motion](../quality/slop-lens-motion-finish.md): you check slow motion or drift
