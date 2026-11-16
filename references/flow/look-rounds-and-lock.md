# Find the look: rounds of mock stills and the lock

Read this file when pictures must settle the look: rounds that change 1 decision, and the lock that records the choice.

## Rounds of mock stills

When no film is behind the words, the user can only react to a picture. Then the mock stills are the main tool.

```sh
python3 SKILL_DIR/scripts/shotspeak.py round --options shotspeak_out/NAME/options.json --base A --vary light
python3 SKILL_DIR/scripts/shotspeak.py mock --options shotspeak_out/NAME/round_1/options.json --dry-run
```

- A round is the same shot 2 to 4 times. Only 1 decision changes: `light`, `grade`, `lens`, `height` or `speed`.
  Test the decision that you are least sure about.
- A round with a paid backend is a paid request. Ask the 1-line cost question each time. The card shows the
  round number and the running total.
- After the user reacts, keep the winner and drop the losers:
  `round --options PATH --base A --keep light=overcast_soft --reject light=hard_backlight --vary height`.
  The script does not show a rejected value again. Do not bring a rejected idea back with a small change.
- `--values a,b,c` selects the values yourself.
- The cap is 3 rounds (`--max-rounds`). It protects the user's money. If the user wants more rounds, raise it.
- With no image backend, use `mock --backend text` for the round: the text diagrams, the plain words and the
  reference links. Say that the look is less certain without pictures.
- `round --options PATH --base A --keep height=high` with no `--vary` saves the last winner.
  The settled option set is `refined.json`.

## The lock

When the user says "that one", offer the lock. It is a record of what the user approved.

```sh
python3 SKILL_DIR/scripts/shotspeak.py lock --options shotspeak_out/NAME/refined.json --pick A \
  --approval "yes - the grey one from above. lock it" --ref "https://..."
```

`look_lock.json` holds: the locked decision for each family; the reference links, as provenance only; the mock
image files with their SHA-256; the number of rounds and the spend; the user's own words; and the time, in its
own field. Write the user's real words. Never write them for the user.

- `choose` shows the status on the final spec: `LOCKED`, `UNLOCKED: decisions may still change`, or
  `LOCK IS STALE` when a decision changed after the lock.
- The final prompt works in all 3 cases. The lock never blocks it.
- A change after the lock needs a new lock, with new words from the user.

## See also

- [References](look-references.md): the user can point to a public example
- [Mock stills](mock-stills.md): you need an image route for a round
- [Lighting](../light-colour/lighting.md): the round varies `light`
- [Grades](../light-colour/grades.md): the round varies `grade`
