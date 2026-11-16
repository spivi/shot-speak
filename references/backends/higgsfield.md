# Backend: Higgsfield API

Read this file when the user has a Higgsfield key: what is verified, and the settings.

**The Higgsfield route is not verified with a live request.** The request shape follows the provider's
client: 1 submit, then status checks on the link of that request. The image endpoint id and its input fields
are not confirmed. The cost is "unknown", so the tool refuses until you set `SHOTSPEAK_EST_USD_PER_IMAGE` or
the user accepts an unknown cost. If the first request fails, use `--backend openai` or the paste path.
Higgsfield moves to the top of the order after 1 live image request confirms the endpoint, the fields and the price.

## Settings

| Setting | Default | Change |
|---|---|---|
| Higgsfield endpoint id | `marketing-studio/image/flare` (not verified) | `SHOTSPEAK_HIGGSFIELD_MODEL` or `--model` |
| Extra request fields | none | `SHOTSPEAK_HIGGSFIELD_EXTRA_INPUT` (a JSON object) |

The Higgsfield, fal.ai and Replicate paths send only the prompt, plus the extra fields. Model input names differ, so the
tool does not guess a size field. The aspect ratio is also written in the prompt text.

## See also

- [Cost and limits](cost-and-limits.md): the unknown-cost rule
- [OpenAI](openai.md): the fallback route
