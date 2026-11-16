# Blocking previs: files and how to read them

Read this file when the command finished: which files exist, and how to check the frames.

## Files

For each option, in `shotspeak_out/NAME/previs/option_X/`:

| File | Content |
|---|---|
| `blocking.py` | The Blender script. Self-contained. The same `options.json` gives the same bytes. |
| `still_start.png`, `still_mid.png`, `still_end.png` | The camera view on the first, the middle and the last frame |
| `plan_overhead.png` | The top view: the camera path in orange, CAM START in green, CAM END in red, each person as a coloured disc with a black arrow for the facing. The camera side is at the bottom. |
| `animatic.mp4` | The move in real time, low resolution. Absent when Blender cannot write video, or with `--no-animatic`. |
| `blocking.blend` | The scene. The user can open it, move the camera and render again. |
| `result.json` | What Blender wrote, and the line-of-sight findings |

`previs/previs.json` is the manifest: the route, the Blender version, and for each option the measured
camera numbers, the framing checks, the notes, and each file with its SHA-256.

To reproduce 1 option from a clean state:

```sh
blender --background --factory-startup --python previs/option_A/blocking.py -- --out previs/option_A
```

## How to read the result

The command prints, for each option: the camera height, the distance and the lens at the start and at the
end, the length of the path, and for the middle frame the screen side and the shot size of each person.

Then open each PNG file and look at it. A finished command is not a correct frame. Check:

1. The person count is correct.
2. Each person is on the expected screen side. The person who faces right is on the left for a fight.
3. No white block points at the lens. The camera sees profiles, three-quarter views or backs.
4. The horizon and the height match the option: a floor-level camera shows a lot of floor.
5. The overhead plan shows the path on 1 side of the people. The path does not pass in front of a face.

Read the notes. Each note is a fact about the option, not a tool error:

- "the head of S2 is outside the frame": the lens is too long or the camera is too near for that group.
  Offer a wider lens or a larger distance.
- "S1 faces the lens": move the camera to a three-quarter position.
- "wall_far hides the head of S2": the place blocks the view. Move the camera or change the place.
- "The camera crosses the action line": left and right flip on screen. Keep the camera on 1 side.

If a note shows a real problem, edit the option in `options.json` and run `previs --only X` again. This costs nothing.

## See also

- [Show it and limits](show-and-limits.md): you show the stills
- [Scene](scene.md): a note asks for a changed option
