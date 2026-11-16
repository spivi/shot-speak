# Listen and interpret

Read this file at the start: what to take from the user's words, and how `plan` turns them into options.

## Listen

Take the user's words as they are. Collect the subject in generic words (and how many people), the action,
the place and the feeling. If something is missing, make a sensible guess and say it. Ask only when the
guess can be badly wrong. The most useful question is "What should the viewer feel?"

## Interpret

```sh
python3 SKILL_DIR/scripts/shotspeak.py plan --phrase "THE USER'S WORDS" \
  --subject "two masked ninjas" --action "at the top of a jump" --setting "a walled courtyard at sunset" \
  --out shotspeak_out/NAME
```

`plan` maps the words to techniques, keeps 1 technique for each family, lets the place name the light,
runs the anti-slop check and writes `options.json` and `options.md`. The same input gives the same output.

Use your judgement on the result. Replace an option that does not fit (`--techniques id1,id2,id3`), or edit
`options.json` by hand. The options are different ideas, not 4 variants of 1 idea.

- **"Like that film."** The user can name a film, a director, a genre or an era. `plan` turns a known name
  into a look recipe: option A is that look as decisions, and the name is removed. Tell the user "what makes
  that look" in plain words. See [the look recipes](../looks/index.md). List recipes with `shotspeak.py looks`.
- **The medium** comes from the user's words: live action by default, or stop-motion, 3D animation, 2D animation
  or illustration. `plan` says it in 1 line. To change it, set `medium` in `options.json`. Do not ask for it.
- **An anti-slop finding** means that an option may contain a generic AI default. It is advice, with a "Fine when"
  note. Fix it, or keep it when it is the user's choice. The script finds words. You judge the picture:
  [the slop guide](../quality/slop-overview.md).

## See also

- [Phrase map](../language/index.md): the words are vague or `plan` found no match
- [Look recipes](../looks/index.md): the user names a film, a director, a genre or an era
- [Camera moves](../camera/index.md): you replace an option or explain a technique
- [Find the look](look-references.md): `plan` prints `UNKNOWN REFERENCE` or `LOOK NOT CLEAR`
