# Lighting setups guide

Read this file when you select or explain the light.

Light is the largest difference between a film frame and an AI-default frame.

## The 4 decisions

1. **Source:** What makes the light? A sun, a window, a lamp, a fire, a screen. Name 1.
2. **Direction:** Where is it, relative to the camera? Behind the subject is strongest. Beside is strong. Behind the camera is flat.
3. **Quality:** Hard (clear shadow edges) or soft (gradual shadows). Hard light draws shapes.
4. **Shadow:** How much of the frame is dark? A third of the frame in true shadow is a good target for a dramatic look.

## Setups

The key in code format is the value used in `scripts/catalog.py`.

| Setup | Plain words | Feels like | Notes for prompts |
|---|---|---|---|
| `hard_backlight` One hard low sun, camera facing into the light | The sun is low and behind the subject. The camera looks toward it. | Drama, heat, a duel | Rims on hair and shoulders. Shadows fall toward the lens. A third of the frame in deep shadow. |
| `blade_of_light` Blade of light | A narrow strip of hard light crosses the eyes. | Focus, threat, a decision | Name the gap or window that makes the strip. The rest of the face is dark. |
| `silhouette_rim` Silhouette with a rim | A black shape against a bright opening, with a thin edge of light. | Mystery, shape | Write "the body stays black". The pose must read as a shape. |
| `low_side_sun` Low hard side sun | Late sun from 1 side. Half lit, half dark. | Energy, texture, sport | Long hard shadows on the ground show the direction. |
| `soft_window` Soft window light from one side | A large window on 1 side. Gentle, with a dark side. | Quiet, honest, intimate | Write "no fill light". The room behind stays darker than the subject. |
| `overcast_soft` Flat overcast daylight | A grey sky. Even light, soft shadows under things. | Real, cold, documentary | The only soft setup that does not read as glow. Keep the colours muted. |
| `top_pool` Pool of top light | 1 lamp above. A circle of light, darkness around it. | Interrogation, a stage, loneliness | The eyes fall into shadow. |
| `practicals_night` Night, practical lights only | Only the lamps that exist in the place. | City night, tension | Each source has a colour and a short reach. Darkness between the sources. |
| `moonlight` Cold moonlight | 1 cold hard source from high up. | Night outdoors, stealth | Most of the frame is dark, with detail in the blacks. |
| `firelight` Firelight | A low warm source from the side. | Warmth, stories, danger | The light falls off fast. |
| `high_key` Bright and even (high key) | Bright and clean, few shadows. | Comedy, product, children's stories | Keep 1 clear direction, so shapes have a light side and a darker side. |

## Rules

- Use 1 strong source. A second source needs a reason and must be weaker.
- Point the camera into the light when the shot allows it.
- Keep the place darker than the light. A dark room with 1 bright opening gives shape to everything.
- Deep blacks hold detail. Do not let the shadows turn grey and milky.
- Do not write "soft glow", "golden glow", "bloom", "haze", "fog", "god rays" or "volumetric light".
  Visible rays need a cause in the scene: dust lifted by the action, in hard backlight.
- Write "matte floor". Generators add glossy, wet floors.
- Allow a small natural flare only when the source is inside the frame.
- Keep the light the same across the shots of 1 scene. State the position of the sun once, for example
  "the sun is low in the south-west, outside the west wall", and derive each shot from it.
- A light event that repeats, such as a strobe, needs exact times.
- The mock image is the fastest test of a light idea. If the mock is flat, the video will be flat.

## See also

- [Colour grades](grades.md): you select the grade
- [Slop tells: camera and light](../quality/slop-camera-light.md): you check the light
- [Camera placement](../camera/placement.md): the camera side depends on the light
