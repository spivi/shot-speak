# Blocking previs: what the scene contains

Read this file when you explain the grey scene, or write a `previs` object by hand.

## What the scene contains

- A floor of 1 m squares in 2 greys. Count the squares to read a distance.
- Grey boxes for the place, from the words of the setting: a courtyard, an alley, a room, an opening, a low
  wall, a table, pillars. The camera side of the action stays open.
- 1 faceless grey mannequin for each person, 1.75 m tall, 4 people at most. A white block on the head shows
  the front. A black stripe shows the back. A colour band on the chest names the person:
  S1 orange, S2 blue, S3 green, S4 purple.
- An animal (a dog, a cat, a horse) gets a simple four-legged stand-in, 0.72 m tall.
- A thrown object, when the action names one ("throws a bone", "catches a ball"): a bone, a ball, a disc or a
  stick from primitives. It flies in from in front of the subject on a real curve of gravity. It arrives at
  the mouth of an animal, or at the hands of a person, on the middle frame. The plan shows the throw as a dashed line.
- A yellow T mark on the floor at each start position.
- 1 camera with a 36 mm wide sensor. The focal length, the height, the distance and the side come from the
  words of the option (`lens` and `placement`). The move has 1 key for each frame at 24 frames for each second.
- Seeded noise for handheld moves. The same option gives the same shake.

The mannequins do not act. A mannequin that travels slides along its path. A mannequin that jumps rises and
falls on a real curve of gravity. The previs shows the route and the timing. The video generator makes the body motion.

Speed in the previs: a frozen moment holds the people almost still while the camera moves. A speed ramp
slows the people in the middle of the shot. A ramp on contact is slow in the first half.

## Options written by hand

The solver reads the height, the distance, the side and the lens from the words of the option. Use the
catalogue wording: "at knee height", "4 m away", "side-on", "three-quarter", "behind", "5 m up".
For exact numbers, add a `previs` object to the option. All keys are optional:

```json
"previs": {"kind": "arc", "az": [150, 40], "d": 3.0, "h": 1.2, "aim_h": 1.3, "duration": 3.0, "roll": 0}
```

`kind` is one of: `locked`, `arc`, `whip`, `zoom`, `dolly`, `dolly_zoom`, `track`, `follow`, `handheld`,
`overhead`, `crane`, `montage`, `pov`, `oner`. `az` is the angle around the subject in degrees: 0 is straight
in front of the face, 90 is side-on, 180 is behind. `d` is the distance in m. `h` is the camera height in m.
`aim_h` is the height of the point that the camera looks at.

## See also

- [Routes](routes.md): which route builds it
- [Files and how to read them](outputs.md): the files it writes
