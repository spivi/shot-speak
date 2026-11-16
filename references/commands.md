# Commands

Read this file when you need the exact command, its options or the exit codes.

| Command | Does |
|---|---|
| `shotspeak.py prompt --phrase "..."` | Fast path: 1 final prompt, no options round. |
| `shotspeak.py plan --phrase "..."` | Writes 3 to 4 distinct options and runs the anti-slop check. |
| `shotspeak.py looks [--search "..."]` | Lists or searches the look recipes. |
| `shotspeak.py refs --query "..."` | Prints search links for public reference sites. Opens nothing. |
| `shotspeak.py round --options PATH --base A --vary light` | A round of 2 to 4 mock stills that differ in 1 decision. `--keep`, `--reject`, `--max-rounds`. |
| `shotspeak.py lock --options PATH --pick A --approval "..."` | Writes `look_lock.json` with the approved decisions. |
| `shotspeak.py detect [--image-tool NAME \| --no-image-tool]` | Shows the image backend and the next step for your case. Never prints a key. |
| `shotspeak.py mock --options PATH --dry-run` | Prints the image prompts, the estimate and the card fingerprint. Sends nothing. |
| `shotspeak.py mock --options PATH --confirm FP` | Generates the mock stills after the user said yes to that card. |
| `shotspeak.py mock --options PATH --backend host` | Prints the prompts and file names for your own image tool. Sends nothing. |
| `shotspeak.py mock --options PATH --backend text` | Copy-ready prompts and text diagrams. Sends nothing. |
| `shotspeak.py mock --options PATH --import option_B=FILE` | Registers an image that the user made. |
| `shotspeak.py blender-detect` | Shows the previs route: `mcp`, `headless` or `none`. Opens no window. |
| `shotspeak.py previs --options PATH [--route R] [--only B]` | Builds the grey-box blocking previs and `previs/previs.json`. |
| `shotspeak.py choose --options PATH --pick B [--mix light=C] [--layout-ref]` | Writes the final shot spec and the prompt block. |
| `shotspeak.py sequence --options PATH --pick B --pattern impact` | Writes a multi-shot prompt with exact cut times. |
| `shotspeak.py deslop --text "..."` | Flags AI-slop tells in a prompt and prints a rewrite. |

Exit codes: `0` done, or an optional stage was skipped; `1` a request or a Blender run failed; `2` refused or
not confirmed; `3` the anti-slop check found something.

## See also

- [The steps](flow/index.md): which command belongs to which step
