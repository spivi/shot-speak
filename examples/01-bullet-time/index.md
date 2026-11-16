# Example 1: "the bullet time thingy"

A complete run, from the user's words to the final prompt block.
The files that the scripts wrote are in [`bullet-time/`](../bullet-time/). No image was generated for this example.
It uses the text-only path, so you can reproduce it without a key: `python3 scripts/build_examples.py`.

## The user's words

> the bullet time thingy where the camera swishes around them mid-air

From the conversation, the agent also knows: 2 masked ninjas, a jump off a low wall, a walled courtyard at sunset.

## The steps

- [Step 1: plan](1-plan.md): Read when you want to see the user's words become 4 options.
- [Step 2: the card for option A, as shown in chat](2-card.md): Read when you want to see how 1 option looks in the chat.
- [Step 3: the mock card (dry run)](3-mock-card.md): Read when you want to see the cost card before a paid request.
- [Step 4: choose](4-choose.md): Read when you want to see the pick, the mix and the final prompt block.
