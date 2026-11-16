# Pick, mix, change

Read this file when the user picks an option, mixes parts or asks for changes.

```sh
python3 SKILL_DIR/scripts/shotspeak.py choose --options shotspeak_out/NAME/options.json --pick B --mix light=C
```

The lens, the light, the grade and the speed can come from another option. `choose` writes `choice.json` and
`final_spec.md`: the decision table, the risks, the prompt block and the 1-line prompt. It works with or
without a lock. Without a lock, the spec says "UNLOCKED: decisions may still change".

Replace the stand-in subject with the user's own subject in generic words. State the exact number of people.
Tell the user that the mock still shows framing and light. It is not a face reference.

## See also

- [Option cards: after the cards](../quality/option-cards.md): other options, a custom option, the final spec
- [Sequences](../sequences/index.md): the user wants more than 1 shot
- [Pitfalls](../quality/pitfalls.md): you write the risks of the final prompt
