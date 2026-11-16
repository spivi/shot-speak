# Example 2: de-slop a prompt

The user pastes a prompt and says: "My videos all look like AI. What is wrong with this?"

## The prompt

```text
cinematic shot of a skateboarder doing a kickflip, slow motion throughout, camera slowly orbiting around him, beautiful lighting, lens flares, ultra detailed, 4k
```

## Step 1: find the tells

```sh
python3 scripts/shotspeak.py deslop --text "cinematic shot of a skateboarder doing a kickflip, slow motion throughout, camera slowly orbiting around him, beautiful lighting, lens flares, ultra detailed, 4k"
```

The script finds 10 tells:

| Group | Tell | Found in the prompt | Why it reads as AI |
|---|---|---|---|
| composition | 180 or 360 degree orbit | orbiting around | A full orbit passes the front of the face, flips left and right on screen, and shows a background the generator must invent. |
| composition | No camera position stated | (not stated) | With no position, the generator selects the centred, front-facing, chest-height default. |
| lighting | Soft, even golden glow | beautiful lighting | Light with no source and no shadow is the standard generator finish. Real light comes from one place and leaves a dark side. |
| lighting | Lens flare everywhere | lens flares | A flare needs a bright source inside or just outside the frame. Flares with no source are decoration. |
| lighting | No light source stated | (not stated) | With no source, the generator fills the frame with even, sourceless light. |
| lens | No lens stated | (not stated) | With no lens, the generator uses the neutral normal lens. |
| motion | Aquarium speed: slow floating camera and slow bodies | slowly orbiting | Generated cameras drift and people move as if under water. Real action is fast, then still. |
| motion | Slow motion everywhere | slow motion throughout | When every shot is slow, no shot is special, and generated slow motion makes bodies float. |
| finish | Over-saturated HDR look | ultra detailed | Quality words push the generator to its showroom finish: glowing colours, crisp everywhere, no black. |
| finish | 'Cinematic' and 'epic' with no direction | cinematic | These words carry no camera, lens or light. The generator answers with all of its defaults at once. |

"(not stated)" means that the prompt leaves the decision to the generator. The generator then uses its default.

The script's rewrite is a starting point. Each `[bracket]` is a decision that is still open:

```text
Shot of a skateboarder doing a kickflip, real time, with one short slow-motion beat at the peak of the action, the camera, in one fast move, arcs about 130 degrees around, never to the front of, him. Camera: [state the height, the side and the distance, for example 'low at knee height, side-on, 3 m away']. Light: [name one source and its direction, for example 'one hard low sun behind the subject'; about a third of the frame in true shadow]. Lens: [state a focal length for a feeling, for example '18 mm on the floor' or '85 mm from far away']. Avoid: nobody looks into the lens; every eyeline goes to a target inside the scene; no slow floating camera drift; the camera is locked or makes one decisive move with a clear end; no soft even glow; one motivated light source with a real dark side; no bloom, no haze, no fog, no volumetric god rays; worn real textures with dust, creases and small defects, nothing plastic or perfectly clean.
```

## Step 2: the agent makes the decisions

The agent asks 1 question, because the answer changes the shot:

> Do you want the trick at normal speed with one short slow-down at the top (recommended, it keeps the
> energy), or the camera moving around him while time is frozen?

The user selects the first choice. The agent fills each bracket from the guides:

| Open decision | The agent's decision | From |
|---|---|---|
| Camera | Locked on the ground, side-on, 3 m away, the lens level | [`camera/placement.md`](../references/camera/placement.md): on the floor for scale, profile for action |
| Lens | 18 mm | [`camera/lens.md`](../references/camera/lens.md): wide, low and close for scale and energy |
| Light | One hard low sun behind him, a third of the frame in shadow | [`light-colour/lighting.md`](../references/light-colour/lighting.md): the camera faces into the light |
| Speed | Real time with a short ramp at the top | [`camera/speed.md`](../references/camera/speed.md): slow motion for 1 beat |
| Camera move | None. The orbit is removed. | [`quality/slop-lens-motion-finish.md`](../references/quality/slop-lens-motion-finish.md): a locked frame is stronger than a slow orbit |
| Finish | Fine grain, true blacks, worn concrete | [`quality/slop-lens-motion-finish.md`](../references/quality/slop-lens-motion-finish.md): no quality words |

## Step 3: the rewritten prompt

```text
A skateboarder kickflips over a low concrete ledge, seen from a locked camera on the ground, side-on, 3 m away, the lens level; 18 mm lens, the rough concrete large in the foreground; one hard low sun behind him, his body rimmed with light, long shadows toward the lens, about a third of the frame in deep shadow; real time into the trick, a short ramp to slow motion at the top of the kickflip, then back to real time for the landing; his eyes stay on the board; fine grain, true blacks, worn dusty concrete. Avoid: nobody looks into the lens; no slow floating camera drift; no bloom, no haze, no fog; real gravity and real jump height, nobody floats.
```

The agent runs `deslop` on the rewrite. Result: `No AI-slop tells found.`

## What changed, in plain words

- "Cinematic" and "ultra detailed, 4k" are gone. They gave no direction. The prompt now describes a film look: grain, true blacks, worn concrete.
- The slow orbit is gone. The camera is locked on the ground, and the trick carries the shot.
- The camera has a place: on the ground, from the side. The skater is not centred and does not face the lens.
- The light has a source: a low sun behind him. A third of the frame is dark.
- Slow motion is 1 short beat at the top of the trick, not the whole shot.
- The decorative lens flares are gone. A small natural flare can still appear, because the sun is in the frame.
