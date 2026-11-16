# Failures and privacy

Read this file when a request fails, or before you send data to a provider.

## Failures

- **Rejected** (an HTTP 4xx answer): the provider refused. The tool stops and sends no more requests. Read the
  message. A content block needs a changed prompt and a new card.
- **Ambiguous** (a timeout, a connection error, an HTTP 5xx answer): the result is unknown and the request can
  have been billed. The tool does not send it again. Tell the user to check the provider's usage page.
- An option whose image file exists is not requested again. Use `--force` only when the user wants a new image.
- `receipts.json` holds the status, the prompt hash and the provider's usage numbers. It never holds a key.

## Privacy

- Never print, log or commit a key. Keep keys in the environment or in an ignored `.env.local`.
  `detect` warns when the key file is not ignored by Git.
- Error messages from providers are redacted.
- If a key appears in the conversation, tell the user to revoke it.
- The only data sent to a provider is the mock image prompt. It contains generic stand-in subjects.
  The tool refuses a subject that contains an email address, a URL, a file path, a key or a protected name.
- Do not put the user's name, a real person's name or a description of a real person's face into a prompt.
- Do not upload the user's photos to make a mock.
- A film or a person that the user names for a look is replaced with a description before a file is written.
- The blocking previs runs on the user's machine. The committed example stills hold no machine data.

## See also

- [Cost and limits](cost-and-limits.md): the cost card
- [Pitfalls: provider filters](../quality/pitfalls.md): a request was blocked
