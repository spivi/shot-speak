# AI video pitfalls

Read this file before you write the "risks" of an option, the final prompt block, or advice about a failed take.

The look problems (composition, light, lens, motion) are in [the slop guide](slop-overview.md). This file covers the rest:
what generators get wrong, what provider filters block, and how to work cheaply.

## What generators get wrong

| Pitfall | What happens | What to write or do |
|---|---|---|
| Front-facing default | The subject turns to the camera. | State the side: "in profile", "three-quarter", "the camera never in front of the face". |
| Eyes into the lens | People look at the viewer. | "Nobody looks into the lens." Give each person an eyeline target. |
| Floating | Jumps go too high and hang. | A real height, "real gravity, no floating". A low camera makes a small jump heroic. |
| Slow-motion overuse | Everything drifts. | State real time. Keep slow motion for 1 beat. |
| Full orbits | Faces pass the lens, left and right flip, the place changes. | A partial arc of about 130 degrees with a named start view and end view. |
| Screen direction flips | A subject who went left to right now goes right to left. | State the direction once. Keep every camera on 1 side of the action. |
| Extra or merged people | A reference sheet with several views becomes several people. Two similar people merge. | State the exact number of people. Give each person a screen side and different clothing. "Never the same face twice." |
| Identity drift | The face changes between shots or during a long shot. | Short shots. 1 person in each shot when the likeness matters. Describe the clothing once and repeat "the same person". |
| Mirrored pairs | 2 people do the same move in sync. | Give each person a different action and a different end pose. |
| A zoom in place of a move | "Push in" becomes a zoom, or the reverse. | Describe the visible result: "the background slides past" or "no parallax". |
| Emotion labels | "She is angry" gives a generic face. | Write what the camera sees: the jaw sets, the eyes narrow on the door. |
| Too many demands | The generator drops some of them. | 1 action, 1 camera strategy and 1 end state in each shot. Fix about 3 things in each revision. |
| Long takes | Rooms and faces change after some seconds. | Keep shots short. Join shots in the edit. |
| Hands, text, small props | They deform. | Keep them simple, still, or out of the close-up. |
| Wide lens tilted up | Bodies stretch. | "The lens level, never tilted up." |
| Invented space | A reveal or an orbit shows a place the generator must invent. | Describe what is there in 1 sentence, or do not show it. |

## Mock images and identity

- A mock image shows **framing, lens feel, light and grade**. It is not a character design.
- Use generic stand-in figures in a mock. Keep faces turned away from the lens.
- **Do not use a mock image as a reference for a face.** The stand-in face will leak into the video and replace
  the real character. If you attach a mock to a video request, give it 1 role in words:
  "composition and light only; ignore the people".
- Do not describe a real person's face in a mock prompt. Do not put a real name in any prompt.
- Do not upload a photo of a real person to make a mock. The mock does not need it.

## Provider filters

Filters differ between providers and change over time. These habits reduce false blocks. They are observations,
not guarantees.

- **Describe shapes, not names.** A brand, a band, an album, a film, a franchise character or a celebrity name
  can trigger a block. Write "a red-and-blue masked acrobat suit", not the character's name.
  A start image that looks like a protected character can also trigger a block.
- **With young performers in the frame, write clothing, stance and action only.** Do not write body, skin,
  breath, "bare" or lying-down words, even when the meaning is innocent. The same scene can pass after those
  words are removed.
- **Keep force clean.** Write "no blood, skin stays clean". Show force with reaction, dust and deformation.
- **A block is not a quality verdict.** If 1 provider blocks a harmless scene, another provider can accept it.
  Check the prompt for ambiguous words first.
- Do not send the same blocked request again without a change. Do not retry a paid request automatically
  when its result is unknown: check the provider's usage page first.

## Work cheaply

Use the cheapest method that answers the open question. Go up 1 level only for a reason.

| Level | Method | Answers |
|---|---|---|
| 1 | Words: positions, facing, screen sides, the side the camera stays on | The order of events. 1 or 2 people in a simple place. |
| 2 | A text diagram: a top view and a frame sketch (this skill, no cost) | Where the camera stands and what the frame holds. |
| 3 | A mock still for each option (this skill) | Lens feel, light and grade. Which option the user wants. |
| 4 | A marked still: the user draws positions and arrows on a frame | Exact start positions for 2 or more people. |
| 5 | A low-resolution draft video | Motion, timing, whether the generator follows the direction. |
| 6 | A 3D previs as a layout reference | An exact camera path, cuts on music beats, several takes that must match. |

- Draft at the lowest resolution. A higher-resolution run is a new take and can differ.
- For action, 2 to 4 drafts of the same prompt give different takes. Select by moment, then cut the best moments together.
- Regenerate only the broken seconds, and join them in the edit. Cut on movement.
- Ask the user for an input when it changes the result more than another attempt: a mark on a still, a choice between 2 options.

## See also

- [The slop guide](slop-overview.md): the look problems: composition, light, lens, motion
- [Sequences](../sequences/index.md): the user wants several shots
- [Option cards](option-cards.md): you present the risks
