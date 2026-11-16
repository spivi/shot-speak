# Image backends: the order and `detect`

Read this file before you generate mock images: which backend comes first, and how `detect` finds it.

## Order

| Priority | Backend | Needs | How |
|---|---|---|---|
| 1 | OpenAI Images API | `OPENAI_API_KEY` | `scripts/shotspeak.py mock` |
| 2 | Higgsfield API | `HF_KEY` | `scripts/shotspeak.py mock --backend higgsfield` |
| 3 | fal.ai (extra) | `FAL_KEY` and `SHOTSPEAK_FAL_MODEL` | `scripts/shotspeak.py mock --backend fal` |
| 3 | Replicate (extra) | `REPLICATE_API_TOKEN` and `SHOTSPEAK_REPLICATE_MODEL` | `scripts/shotspeak.py mock --backend replicate` |
| 4 | Your own image tool or connector | A harness that has one | `mock --backend host`, then you call the tool |
| 5 | Copy and paste | Nothing | `mock --backend text`, then `mock --import` |

Run `python3 scripts/shotspeak.py detect` first. It reads the process environment, then `.env.local`, then `.env`
in the working folder. It prints the backend and the source of the key. It never prints the key.

Copy [`.env.example`](../../../.env.example) to `.env.local`. Keep that file out of Git.

With several keys, OpenAI is selected first, then Higgsfield, then fal.ai, then Replicate.
Use `--backend` to select another.

## See also

- [OpenAI](openai.md): a key exists
- [Host tool or paste](host-and-paste.md): no key exists
- [Cost and limits](cost-and-limits.md): before a paid request
