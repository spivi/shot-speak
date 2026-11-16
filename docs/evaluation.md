# How to evaluate shot-speak

Read this file before you claim that a change makes better prompts or better videos.

The examples in `examples/` are demonstrations. Each one is 1 take of 1 model. They show what the tool does.
They do not prove that the tool is better on average. This file gives a small protocol that anyone can repeat.

## 1. Offline checks: what code can prove

These checks need no key and no network. `python3 -m unittest discover -s tests -v` runs them.

| Property | How it is checked | Where |
|---|---|---|
| A clean prompt is not changed | The exact text comes back from `deslop` | `tests/fixtures/prompt_cases.json` |
| A rewrite is stable | `deslop` on its own rewrite changes nothing | `tests/test_slop_context.py` |
| A chosen technique is kept | Fog in the story, an interview, stop-motion, a product turntable | `tests/fixtures/prompt_cases.json` |
| A negation is respected | "no fog" is never rewritten | `tests/fixtures/prompt_cases.json` |
| A prompt follows its decisions | An edit of a decision reaches the card, the fingerprint and the final prompt | `tests/test_integrity.py` |
| A prompt never forbids what the user asked for | Fog in the place gives no "no fog" clause | `tests/test_slop_context.py` |

To add a case, add 1 entry to `tests/fixtures/prompt_cases.json`: the text, the exact tell ids that must be flagged
and kept, and the words that the rewrite must keep or remove.

These checks prove properties of the text. They do not prove that a video looks better.

## 2. Prompt comparison: what a reader can judge

For 1 idea, write 3 prompts, as each scene in `examples/*/tiers.json` does:

1. **First prompt:** the words as a user types them.
2. **Clear prompt:** a careful description with no film language.
3. **shot-speak prompt:** the `prompt_block` from `choose`, or the `prompt` fast path.

Count, for each prompt, the decisions that it states. Use `deslop --json` on each prompt: each `missing_*` tell is a
decision that the prompt leaves to the generator.

| Decision | Stated? |
|---|---|
| Camera position: height, side and distance | yes or no |
| Lens | yes or no |
| Light source and direction | yes or no |
| Speed | yes or no |
| Camera move with a start and an end | yes or no |
| Colour grade | yes or no |

Also record the length in words. A longer prompt is not a better prompt. Note each clause that states no decision.

## 3. Video evaluation: what only people can judge

Send the 3 prompts of 1 idea to the same model, with the same settings, the same references and the same number of
takes. Show the takes to 3 or more people who do not know which prompt made which take. Use the same order of
questions for each take. Score each question 1 to 5.

| # | Question | What a high score means |
|---|---|---|
| 1 | Intent | The take shows what the user asked for |
| 2 | Camera | The camera position, the lens feel and the move match the prompt |
| 3 | Timing | The speed, the slow beat and the cut times match the prompt |
| 4 | Physics | Bodies have weight; nothing floats; contact looks real |
| 5 | Composition | The frame has a point of view; the subject is placed on purpose |
| 6 | Consistency | Faces, clothes, props and screen direction stay the same over time |
| 7 | Fit | The style fits the request (live action, animation, a commercial) |

Record: the model and its version, the settings, the seed when the model has one, the date, each prompt hash, and
each take hash. Keep the scores per take. Report the spread of scores, not only the mean.

## Limits

- 1 take of 1 model is an anecdote. Use 3 or more ideas and 2 or more takes for each prompt before a claim.
- Models change often. A result is true for the model version that you tested.
- Some models ignore lens and camera words. A low camera score can be a model limit, not a prompt fault.
- No automated score in this repository judges a video. Questions 1 to 7 need people, or a multimodal model that
  you validate against people first.

## See also

- [The examples](../examples/index.md): 1 idea, 3 prompts, 3 real videos
- [The slop guide](../references/quality/slop-overview.md): the tells and when each one is fine
