# Sequence: Build to a peak

3 shots that get closer and shorter, then the peak, then a still ending.

Hero shot: option A. Length: 10 s. Cuts at: 2.5, 4.5, 5.5, 8.5 s.

| # | Time | Shot | Camera | What happens | Speed |
|---|---|---|---|---|---|
| 1 | 0 to 2.5 s | wide shot, 24 mm | locked, far back, side-on | he pedals hard toward the cliff edge | real time |
| 2 | 2.5 to 4.5 s | medium shot, 50 mm | side-on tracking at the subject's speed | the front wheel leaves the edge and he flies out over the drop | real time |
| 3 | 4.5 to 5.5 s | close detail, 85 mm | locked, side-on, tight on the feet, the hands or the object | in the air he pushes the bike away from his body and the bike falls away | real time |
| 4 | 5.5 to 8.5 s | Low-angle wide shot, 18 mm (hero) | locked: the camera does not move, the action comes to it; on the floor, 3 m away, the lens level and looking along the ground into the light | he drops from the top of the wall and lands in a clean superhero landing, dust bursts out | slow motion for this one beat only; real gravity, weight and cloth move truthfully, nothing floats |
| 5 | 8.5 to 10 s | wide shot, 24 mm | locked, low at knee height, three-quarter from behind | he rises slowly into a confident stand and looks up at the cliff edge he jumped from | real time |

## Prompt block

```text
SEQUENCE: 10 s, 16:9 frame. 5 shots joined by 4 hard cuts at exactly 2.5, 4.5, 5.5, 8.5 s.
ONE ACTION AND ONE CAMERA MOVE IN EACH SHOT. Each cut comes when the motion of its shot ends.
SUBJECT AND ACTION: a young man in a grey hoodie and jeans rides a mountain bike off a cliff edge, lets go of the bike in mid-air and lands on the ground below in a superhero landing, in a rocky desert canyon at late afternoon.
PEOPLE: exactly 1. Nobody looks into the lens: the eyes stay on a target inside the scene.
STAGE: the whole action stays within 2 m of the cliff edge. The camera stays on 1 side of the action for every shot.
LIGHT: one hard low sun as the only strong light, behind the subject; the camera faces into the light; bright rims on hair and shoulders, long shadows that fall toward the lens, about a third of the frame in deep true shadow. The same light direction in every shot.
COLOUR: bleach-bypass look: high contrast, low saturation, silvery highlights, dense blacks, visible grain. The same grade in every shot.
SPEED RULE: real time; the only slow beat is the speed of the hero shot.
SHOT LIST:
  1. 0 to 2.5 s | wide shot, 24 mm | camera: locked, far back, side-on | action: he pedals hard toward the cliff edge | speed: real time
  2. 2.5 to 4.5 s | medium shot, 50 mm | camera: side-on tracking at the subject's speed | action: the front wheel leaves the edge and he flies out over the drop | speed: real time
  3. 4.5 to 5.5 s | close detail, 85 mm | camera: locked, side-on, tight on the feet, the hands or the object | action: in the air he pushes the bike away from his body and the bike falls away | speed: real time
  4. 5.5 to 8.5 s | Low-angle wide shot, 18 mm | camera: locked: the camera does not move, the action comes to it; on the floor, 3 m away, the lens level and looking along the ground into the light | action: he drops from the top of the wall and lands in a clean superhero landing, dust bursts out | speed: slow motion for this one beat only; real gravity, weight and cloth move truthfully, nothing floats
  5. 8.5 to 10 s | wide shot, 24 mm | camera: locked, low at knee height, three-quarter from behind | action: he rises slowly into a confident stand and looks up at the cliff edge he jumped from | speed: real time
FIRST FRAME: [where each person stands and what each person holds at 0 s].
LAST FRAME: [where each person is at the end; hold it still]. Use this frame as the start of the next clip.
AVOID: not a default eye-level medium shot; no soft even glow; one motivated light source with a real dark side; nobody looks into the lens; every eyeline goes to a target inside the scene; no slow floating camera drift; the camera is locked or makes one decisive move with a clear end; real gravity and real jump height, nobody floats; no bloom, no haze, no fog, no volumetric god rays; real time, with slow motion only where the shot states it; worn real textures with dust, creases and small defects, nothing plastic or perfectly clean.
```

Replace each of the 2 `[brackets]` with a decision before you use the prompt.
