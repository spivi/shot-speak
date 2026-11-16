# Backend: OpenAI Images API

Read this file when `detect` finds an OpenAI key: the API path and its settings.

With an OpenAI key, `detect` selects this backend first. Run `mock` with no `--backend`.

The default model is `gpt-image-2.5-flare`. It is the model that this skill's source workspace used for its own
storyboard mocks. Change it with `SHOTSPEAK_OPENAI_MODEL=<model id>` or `--model <model id>`.
Default size: `1536x864` for 16:9. Default quality: `medium`. Change them with `--size` and `--quality`.

## Settings

| Setting | Default | Change |
|---|---|---|
| OpenAI model | `gpt-image-2.5-flare` | `SHOTSPEAK_OPENAI_MODEL` or `--model` |
| Size | from the aspect: 16:9 is `1536x864` | `--size WIDTHxHEIGHT` |
| Quality (OpenAI) | `medium` | `--quality low|medium|high` |

## See also

- [Cost and limits](cost-and-limits.md): the cost card and the confirm step
- [Failures and privacy](failures-and-privacy.md): a request failed or a key leaked
