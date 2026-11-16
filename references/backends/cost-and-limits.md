# Cost card and limits

Read this file before a paid request: the cost question, the fingerprint and the caps.

## Before a paid request

1. Run `mock ... --dry-run`. It prints each prompt, the model, the number of images, the estimate with its
   basis and a card fingerprint. It sends nothing.
2. Ask in 1 line: "4 mock stills, about 0.28 USD - go?" The estimate is not a provider quote. Say so when
   the user asks about the price.
3. After a clear yes, run the same command with `--confirm FINGERPRINT`. The fingerprint covers the backend, the
   model, the size, the quality, every prompt and the extra input fields. If 1 of them changes, the tool refuses.
   Ask again with the new number.

The host path and the paste path send nothing from this tool.

The estimate for the default model is 0.07 USD for each image, 0.28 USD for 4. It is a planning estimate, not a
provider quote. Its basis: measured token costs of 0.04 to 0.07 USD for text-only images of the same model family at
a larger size and a higher quality. The provider bills by tokens, so the real cost can differ.
Set your own figure with `SHOTSPEAK_EST_USD_PER_IMAGE`.

After an OpenAI request, `receipts.json` records the provider's token usage and the cost at the published token
rates: 5 / 8 / 30 USD for each 1 million text input / image input / image output tokens, read in November 2026.
Check the current rates at the provider.

The blocking previs, the sequence, the look recipes and the de-slop mode cost nothing.

## Reuse of an image

An image is reused, with no request, only when 2 conditions are true. Its receipt names the same request: the
backend, the model, the size, the quality, the prompt and the extra fields. Its file still has the hash in the
receipt. A file with no receipt, or with a different receipt, is requested again and replaced. An image that the user
imported is kept for the prompt that it was imported for. `--force` requests every image again.

## Limits

| Limit | Default | Change |
|---|---|---|
| Images in 1 run | 4 | `--max-images N` or `SHOTSPEAK_MAX_IMAGES` |
| Estimated cost of 1 run | 1.00 USD | `--max-usd X` or `SHOTSPEAK_MAX_USD` |
| Rounds of mock stills | 3 | `--max-rounds N` or `SHOTSPEAK_MAX_ROUNDS`, when the user asks |
| Unknown cost | Refused | `SHOTSPEAK_EST_USD_PER_IMAGE`, or `--accept-unknown-cost` after the user accepted |

## See also

- [Failures and privacy](failures-and-privacy.md): a request failed
- [Rounds of mock stills](../flow/look-rounds-and-lock.md): each round is a paid request
