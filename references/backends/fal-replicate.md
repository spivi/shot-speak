# Backends: fal.ai and Replicate (extra)

Read this file when the user has a fal.ai or Replicate key: the settings and the extra fields.

## Settings

| Setting | Default | Change |
|---|---|---|
| fal.ai model | none | `SHOTSPEAK_FAL_MODEL` or `--model` |
| Replicate model | none | `SHOTSPEAK_REPLICATE_MODEL` (`owner/name`) or `--model` |
| Extra request fields | none | `SHOTSPEAK_FAL_EXTRA_INPUT`, `SHOTSPEAK_REPLICATE_EXTRA_INPUT` (JSON objects) |

The Higgsfield, fal.ai and Replicate paths send only the prompt, plus the extra fields. Model input names differ, so the
tool does not guess a size field. The aspect ratio is also written in the prompt text.

## See also

- [Cost and limits](cost-and-limits.md): the unknown-cost rule
- [Order and detect](order-and-detect.md): which backend is selected first
