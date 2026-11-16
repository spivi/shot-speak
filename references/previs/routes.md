# Blocking previs: when to use it and the routes

Read this file before you run `shotspeak.py previs`: when it helps, and which route to take.

A blocking previs is a grey-box scene. It shows where the people stand, where the camera is, what the lens
sees and how the camera moves. It is free and local. It is optional. The mock stills never wait for it.

## What it answers

| Question | Mock still | Blocking previs |
|---|---|---|
| What does the shot look like: light, colour, mood? | Yes | No |
| Is the framing possible with this lens at this distance? | A guess | Yes, measured |
| Where does the camera start and stop? How long is the move? | No | Yes |
| Which side of the frame is each person on? | A guess | Yes |
| Does a wall or an object hide a person? | No | Yes, for the 3 stills |

Use the previs when the camera path, the lens or the positions are the open question. For a look question,
the mock still is enough. Do not build a previs for a detail insert: it shows a grey shape.

## Routes

Run `python3 SKILL_DIR/scripts/shotspeak.py blender-detect`. It opens no window. It reports 1 route.

| Route | Condition | What you do |
|---|---|---|
| `mcp` | A Blender MCP add-on answers on its socket, and your tool list has a Blender MCP tool that runs Python code | Run `previs --route mcp`. Send each printed code block through that tool. Then run `previs --route mcp --collect`. |
| `headless` | A local Blender exists and no MCP add-on answers, or you have no Blender MCP tool | Run `previs --route headless`. The script starts Blender without a window for each option. |
| `none` | No Blender | Run `previs` anyway. It writes the scripts and reports the skip. Tell the user that the previs was skipped, and why. |

Rules:

- The socket check finds the add-on. It does not find your tools. If the socket is open but you have no
  Blender MCP tool, use `--route headless`.
- If an MCP call fails or does not answer in 60 seconds, stop. Use `--route headless`. Do not send the same
  block again.
- Never start the Blender window. Never ask the user to open Blender for this stage.
- In the `mcp` route, each block builds a new scene named `shotspeak_option_X`. It does not delete or change
  the user's open scene.
- The socket is `localhost:9876` by default. Change it with `--mcp-host` and `--mcp-port`, or with
  `SHOTSPEAK_BLENDER_MCP_HOST` and `SHOTSPEAK_BLENDER_MCP_PORT`. Set the program path with `--blender` or `BLENDER`.

## The quick path

Offer it when the camera path, the lens or the positions are the open question, and a local Blender exists.

```sh
python3 SKILL_DIR/scripts/shotspeak.py blender-detect
python3 SKILL_DIR/scripts/shotspeak.py previs --options shotspeak_out/NAME/options.json
```

- Route `mcp`: use it only when your tool list has a Blender MCP tool that runs Python code. Send each printed
  block through that tool, then run `previs --route mcp --collect`. If the tool fails, use `--route headless`.
- Route `headless`: the script runs Blender without a window. Never open the Blender window.
- Route `none`: say that the previs was skipped, and why. Go on with the mock stills.

Open the PNG files and look at them before you show them. A finished command is not a correct frame.
The grey frames show framing, lens, camera path and positions. They never show the look or a person's identity.

## See also

- [What the scene contains](scene.md): you build or edit the options
- [Files and how to read them](outputs.md): the command finished
- [Sequences: blocking levels](../sequences/blocking-and-references.md): you pick the cheapest method
