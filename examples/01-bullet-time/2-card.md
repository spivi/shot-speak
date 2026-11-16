# Example 1, step 2: the card for option A, as shown in chat

**Option A: Frozen-moment arc (bullet time) (recommended)**

- **In plain words:** Time almost stops and the camera sweeps part of the way around the subject.
- **What the viewer feels:** The viewer gets a held breath: one instant, seen from more than one side.
- **Pro term to learn:** Frozen-moment arc (bullet time)
- **Choose it when:** One peak moment in the whole piece: the top of a jump, the instant before a landing or a hit.
- **Camera movement:** a fast, smooth arc of about 130 degrees around the subject: it starts behind the shoulder, passes the profile and stops at a front three-quarter view; it never reaches a view straight in front.
- **Camera placement:** at the subject's own height, the lens level, 2 to 3 m away, on one side of the action for the whole move.
- **Lens:** 35 mm. Wide enough to feel the camera travel past the background, not so wide that bodies bend at the frame edge.
- **Light:** One hard low sun, camera facing into the light. A single low, hard sun behind the subject. The camera looks toward it.
- **Colour grade:** Film print, deep blacks. Looks like real film: fine grain, true black shadows, natural colour.
- **Speed:** Frozen moment. Time almost stops while the camera keeps moving.
- **AI look it avoids:** 180 or 360 degree orbit; Floating, weightless bodies.
- **Risks with AI video generators:**
  - A full 180 or 360 degree orbit turns faces into the lens and flips left and right on screen. Ask for about 130 degrees.
  - Generators let frozen bodies float upward. Write 'real gravity, drifting only a hand's width'.
  - The background behind the subject is invented during the move. Keep the place simple.
- **Say this to a video model:**

```text
Two masked ninjas at the top of a jump off a low wall; time almost stops while the camera sweeps a fast, smooth arc of about 130 degrees around them at their own height, lens level, from behind the shoulder past the profile to a front three-quarter view; 35 mm lens; one hard low sun as the only strong light, behind the subject; the camera faces into the light; bright rims on hair and shoulders, long shadows that fall toward the lens, about a third of the frame in deep true shadow; photochemical film look: fine grain, deep true blacks with detail, natural skin and material colours, restrained saturation; time almost stops: the subject drifts only a hand's width while the camera moves fast; real gravity returns at the end of the move. Avoid: the camera never completes a half circle and never reaches a view straight in front of the face; real gravity and real jump height, nobody floats; nobody looks into the lens; every eyeline goes to a target inside the scene; no slow floating camera drift; the camera is locked or makes one decisive move with a clear end; no bloom, no haze, no fog, no volumetric god rays.
```

With no image backend, the card shows the text diagram:

```text
   TOP VIEW             light, behind the subject
                              |
                              v
                 S ->              S = subject, faces and moves ->
      C1                           C1 = camera start, behind the shoulder
        '.                         C2 = camera at the profile, side-on
          ' .                .C3   C3 = camera end, front three-quarter
             ' - . C2 . - '        The camera stays on this side of S.
                                   It never reaches the front of the face.

   FRAME SKETCH
   +------------------------------+
   |                              |
   |        o>     o>             |
   |       /|     /|        *sun  |
   |       / \    / \             |
   |______________________________|
   +------------------------------+
```

Why about 130 degrees and not a half circle: at 180 degrees the camera passes the front of the faces, the
ninjas look into the lens, and their direction of travel flips on screen. The arc starts behind the shoulder
and stops at a front three-quarter view. The faces stay in profile and the direction holds.

## See also

- [Example 1: the steps](index.md): the user's words and the other steps
- Next: [Step 3: the mock card (dry run)](3-mock-card.md)
