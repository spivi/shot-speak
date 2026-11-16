# Failures and privacy

Read this file when a request fails, or before you send data to a provider.

## Failures

- **Rejected** (an HTTP 4xx answer): the provider refused. The tool stops and sends no more requests. Read the
  message. A content block needs a changed prompt and a new card.
- **Ambiguous** (a timeout, a connection error, an HTTP 5xx answer): the result is unknown and the request can
  have been billed. The tool does not send it again. Tell the user to check the provider's usage page.
- **A bad answer** (empty, cut off, not 1 complete PNG, JPEG or WebP image, larger than 50 MB): ambiguous. Nothing is
  saved. A new image is written in 1 step, so a stopped run never leaves half a file.
- An option whose image was made by the same request, with the same bytes, is not requested again. See
  [Cost and limits](cost-and-limits.md). Use `--force` only when the user wants a new image.
- `receipts.json` holds the latest receipt of each option: the status, the request and prompt hashes, the image hash,
  the format and the provider's usage numbers. It is written after each request. It never holds a key.

## Privacy

- Never print, log or commit a key. Keep keys in the environment or in an ignored `.env.local`.
  `detect` warns when the key file is not ignored by Git.
- Error messages from providers are redacted.
- If a key appears in the conversation, tell the user to revoke it.
- What leaves the machine for 1 image: the key header, and a JSON body. For OpenAI the body is the model, the prompt,
  the size, the quality and `n: 1`. For Higgsfield, fal.ai and Replicate it is the prompt and the extra fields of
  `SHOTSPEAK_<NAME>_EXTRA_INPUT`. The image link in the answer is then opened, with no key. Only an https link is opened.
- The extra fields cannot set the prompt or the number of images. A key or a value with a link, a file path, an email
  address, a key or a protected name is refused, so no user photo goes out this way.
- The tool refuses a prompt, a subject or an extra field that contains an email address, a URL, a file path, a key or a
  protected name. These checks are word patterns. They cannot find every name or every private fact, for example
  a person's name that is not on the list. Read each prompt on the card before the yes.
- Do not put the user's name, a real person's name or a description of a real person's face into a prompt.
- Do not upload the user's photos to make a mock.
- A film or a person that the user names for a look is replaced with a description before a file is written.
- The blocking previs runs on the user's machine. The committed example stills hold no machine data.

## See also

- [Cost and limits](cost-and-limits.md): the cost card
- [Pitfalls: provider filters](../quality/pitfalls.md): a request was blocked
