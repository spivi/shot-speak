# Backends: host tool, Codex image tool and paste

Read this file when no key exists: use your own image tool, or let the user paste the prompts.

## Which path to use

Look at your own tool list to know your case. Do not guess from the operating system or from file paths.
Tell `detect` what you see: `detect --image-tool NAME` or `detect --no-image-tool`. It prints the next step.

1. **`detect` finds a key.** Use the API path. Ask the 1-line cost question first (see [cost and limits](cost-and-limits.md)).
2. **No key, and you have an image tool.**
   - **In Codex**, the built-in image generation tool is `image_gen` (the imagegen skill). It needs no key.
   - **With an image connector** in your tool list, for example a Higgsfield connector, use that connector.
     Ask the cost question first when the connector spends the user's credits.
   - Run `mock --backend host`. It prints the prompts and the target file names. Call your tool 1 time for
     each option with the exact prompt. Save each result in the output folder as `option_A.png`,
     `option_B.png` and so on. Then show the images in chat.
3. **No key and no image tool.** This is the usual case in Claude without a connector.
   - Tell the user in 1 or 2 friendly sentences: the mock stills need an image model, and there are 2 ways.
   - Way 1: add an OpenAI or Higgsfield key to `.env.local`.
   - Way 2: paste the ready prompts into any image tool that the user has.
   - Run `mock --backend text`. It prints 1 copy-ready prompt and 1 file name for each option.
   - When the user has the images, register them:
     `mock --options PATH --import option_A=FILE --import option_B=FILE`.
     The cards, the previs comparison and the lock then use them. PNG, JPEG and WebP files are accepted.

The user always gets the option cards and the prompts. A missing image never stops the session.

## See also

- [Order and detect](order-and-detect.md): `detect --image-tool`
- [OpenAI](openai.md): the user adds a key later
