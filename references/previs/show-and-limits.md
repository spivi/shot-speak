# Blocking previs: show it, the layout reference and limits

Read this file when you show previs stills, use one as a layout reference, or state its limits.

## How to show it

Show each option's mock still first. Put its previs stills beside it: start, middle, end, then the overhead plan.
Say 1 sentence about what the previs measured, for example:
"With the 85 mm lens at 2 m, the frame holds 1 head and 1 fist. The second person is outside the frame."

Tell the user the rule:

> The grey frames show framing, lens, camera path and positions only. They do not show the look, the light,
> the colour or a person's identity.

## Use as a layout reference (optional, free)

Some video tools accept a start frame, an end frame or a layout reference. `choose` lists the previs files of
the picked option in `final_spec.md`. `choose --layout-ref` also adds a layout line to the prompt block.

- Give the reference 1 job in the prompt: camera position, framing and positions. Say what to ignore: grey
  surfaces, the checker floor, mannequin shapes, colours and light.
- A layout reference controls camera, framing and positions. It does not control contact, anatomy,
  expression or the final light.
- After the first generated take, check for grey-box leakage: flat grey surfaces, a checker floor, box
  shapes or faceless bodies in the picture. If you see leakage, remove the reference and describe the
  layout in words.
- Never use a previs frame as a face, wardrobe or style reference.
- If the lens or the speed came from another option in a mix, run `previs` again before you use the frame.

## Limits

- The scene is a sketch of the place from keywords. It is not the user's real location.
- The line-of-sight check tests the head of each person on the 3 stills only.
- A focal length in Blender is exact. A video generator follows a lens only approximately.
- The `mcp` route and a Blender older than 4.2 are not verified by the tests of this skill.

## See also

- [Option cards](../quality/option-cards.md): the full card
- [Files and how to read them](outputs.md): you check the frames first
