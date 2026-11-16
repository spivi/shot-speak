# Mock stills

Read this file when you make the mock stills: which route applies, and what to tell the user.

```sh
python3 SKILL_DIR/scripts/shotspeak.py detect
```

Look at your own tool list to know where you are. Do not guess from the operating system.

| Case | What you do |
|---|---|
| An OpenAI or Higgsfield key exists | `mock --options PATH --dry-run`, ask the 1-line cost question, then `mock --options PATH --confirm FINGERPRINT` |
| No key, and you have a built-in image tool (Codex: `image_gen`, the imagegen skill) or an image connector | `mock --options PATH --backend host`. Make 1 image for each printed prompt with your tool. Save each image at the printed path. Ask the cost question first when your tool is paid. |
| No key and no image tool (Claude, usually) | Tell the user in 1 or 2 friendly sentences that the mock stills need an image model. Offer the 2 ways: an OpenAI or Higgsfield key in `.env.local`, or paste the ready prompts into any image tool. `mock --options PATH --backend text` prints 1 copy-ready prompt and 1 file name for each option. |

When the user comes back with images: `mock --options PATH --import option_B=FILE`. The cards, the previs
comparison and the lock then use them. With no image, the text diagrams carry the session. Nothing is blocked.
Read [the backends index](../backends/index.md) once before the first paid request.

## See also

- [Backends](../backends/index.md): the order, the cost card, the limits, the privacy rules
- [Host tool or paste](../backends/host-and-paste.md): no key exists
- [Present](present.md): the stills or diagrams are ready to show
