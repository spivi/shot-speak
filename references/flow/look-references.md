# Find the look: references

Read this file when the user's words do not give a clear picture. This is a way to help. It is not a gate.

`plan` prints `UNKNOWN REFERENCE` when the user named something that has no recipe, and `LOOK NOT CLEAR` when
the words name only a mood ("epic but sad"). You can also decide this yourself. Then help the user find the look:

- **References.** Look for 3 to 5 public references and show them as links, each with its source, what it
  shows and why it matches. Take decisions in words from each one. `shotspeak.py refs --query "..."` prints
  search links when you have no web tool. Links only: no login, no download, no still or title to a generator.
- **Rounds of mock stills.** When no film is behind the words, pictures do the work. Each round shows the same
  shot 2 to 4 times with 1 decision changed: `shotspeak.py round --options PATH --base A --vary light`.
- **Lock.** When the user says "that one", offer to lock it: `shotspeak.py lock ... --approval "THEIR WORDS"`.

The details follow. This step is an offer. If the user steers, follow.

If the user steers ("no, just make it darker"), follow the user and skip the rest.

## When to use it

| Signal | Path |
|---|---|
| `plan` prints `UNKNOWN REFERENCE`: the user named a film, a show or a person with no recipe | Reference search |
| `plan` prints `LOOK NOT CLEAR`: the words name only a mood, for example "epic but sad" | Rounds of mock stills |
| You see that the 4 options are guesses | Either path, or both |

The test in the script is simple and always gives the same answer: no phrase matched, or only mood words
matched. You can overrule it in both directions.

Never invent a recipe for a title that you do not know. Say that you do not know it, then look or ask.

## Reference search

Use your own web search or fetch tool. Look in public sources:

| Source | Good for | Rule |
|---|---|---|
| Film-Grab | Free galleries of stills, film by film | Browse. Do not download. |
| Shot Cafe | Free stills by colour, lens and shot size | Browse. Do not download. |
| Stills Lab | Stills with notes on framing and light | Free pages. Do not download. |
| Frameset | Frames from films, ads and music videos | Free pages only. Do not log in. |
| StudioBinder guides | Explanations of shots, lenses and light | Read. |
| American Cinematographer | How a crew made a look | Read. |
| ShotDeck | A large tagged library, with an account | Give a search link only. |
| General web search | Everything else | Open pages only. |

Give the user 3 to 5 candidates. For each one:

1. the link and the source;
2. what the picture shows, in 1 line;
3. why it matches the user's words, in 1 line;
4. the decisions that you take from it, in words: framing, camera height, lens feel, camera move, light
   (direction, hardness, contrast), colour, speed, texture.

Then ask: "Which of these is close? You can mix: the light of 2 with the framing of 4."
When the user picks, rejects or mixes, update the decisions. Put them in the options with `--techniques`, a
mix, or a hand edit of `options.json`.

With no web tool, run:

```sh
python3 SKILL_DIR/scripts/shotspeak.py refs --query "the user's words"
```

It prints 1 search link for each source. It opens nothing. The user browses and tells you what is close.

Rules for references:

- Links only. Never download, store or share a still.
- Never log in. Never read a paid or login-gated library with a tool.
- Never send a still, a title or a link to a generator. Only your own words go into a prompt.
- A reference link can go into `look_lock.json` as provenance. It goes into no other file.

## See also

- [Rounds and the lock](look-rounds-and-lock.md): no film is behind the words, and pictures must do the work
- [Look recipes](../looks/index.md): the user names a film that has a recipe
- [Backends](../backends/index.md): a round of mock stills needs an image tool
