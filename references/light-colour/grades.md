# Colour grade guide

Read this file when you select or explain the colour grade.

The grade is the last decision. It supports the light. It cannot repair a flat light.

## Grades

The key in code format is the value used in `scripts/catalog.py`.

| Grade | Plain words | Feels like | Pairs well with |
|---|---|---|---|
| `film_deep_blacks` Film print, deep blacks | Fine grain, true black shadows, natural colour | Serious, timeless, real | Hard backlight, blade of light |
| `bleach_bypass` Bleach bypass | High contrast, washed-out colour, silvery highlights | Harsh, war, sport, grit | Silhouette, low side sun |
| `cool_desat` Cool and desaturated | Grey-blue, quiet, low saturation | Cold, lonely, clinical | Overcast, moonlight |
| `warm_natural` Warm natural | Warm where the sun lands, neutral shadows | Memory, summer, family | Low side sun, firelight |
| `monochrome` Black and white | No colour. Shape and light only | Graphic, classic, strict | Silhouette, top light |
| `muted_earth` Muted earth tones | Browns, greys, dull greens | Worn, humble, documentary | Window light, overcast |
| `neon_noir` Neon noir | 2 saturated lamp colours against black | City night, danger | Practical lights at night |
| `pastel_soft` Soft pastel | Light matte colours, gentle contrast | Storybook, comedy, calm | High key, window light |
| `teal_orange` Teal and orange | Orange skin against blue-green shadows | Blockbuster | Use it only on purpose. It is the generator default for "cinematic". |

## Rules

- Select the grade from the story, not from the word "cinematic".
- Keep true blacks in every grade. Grey, lifted shadows look like a filter.
- Restrain the saturation. Over-saturated colour with detail everywhere is the HDR look of generated images.
- Use 1 grade for a whole scene. A change of grade means a change of time or place.
- Add fine grain and worn textures. Clean, perfect surfaces look rendered.
- Describe the grade by its visible result: "grey-blue shadows, neutral skin, low saturation".
  Do not name a film, a director or a camera brand.
- Warm does not mean an orange wash. Warm highlights with neutral shadows look real.
- An old take with a flat look can often be graded toward the selected look in the edit. That costs no new generation.

## See also

- [Lighting setups](lighting.md): the grade must support the light
- [Slop tells: lens, motion and finish](../quality/slop-lens-motion-finish.md): you check the finish
