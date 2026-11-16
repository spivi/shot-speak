#!/usr/bin/env python3
"""Render the blocking-previs stills of the worked examples. Needs a local Blender. Opens no window.

    python3 scripts/build_previs_examples.py            # every example
    python3 scripts/build_previs_examples.py SLUG ...   # some examples

For each example it runs the real ``previs`` command at 480 pixels, keeps the 4 stills and the manifest,
and removes the scene file, the script and the movie: a scene file holds data of the machine that made it.
``build_examples.py --check`` then proves that each manifest matches the script that this version generates.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shotspeak as S  # noqa: E402
from build_examples import capture  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
# slug -> the options to render. None renders every option.
RENDER = {"bullet-time": None, "dog-bullet-time": None, "alley-fight": None,
          "skate-kickflip": "A", "birthday-candles": "A", "named-look": "A"}
SIZE = 480


def main():
    wanted = sys.argv[1:] or list(RENDER)
    _code, text = capture(["blender-detect"])
    print(text, end="")
    if "Previs route: none" in text:
        print("No Blender. Nothing was rendered.")
        return 1
    failed = 0
    for slug in wanted:
        folder = EXAMPLES / slug
        argv = ["previs", "--options", str(folder / "options.json"), "--route", "headless", "--size", str(SIZE), "--no-animatic"]
        if RENDER[slug]:
            argv += ["--only", RENDER[slug]]
        code, out = capture(argv)
        failed += code != 0
        previs = folder / "previs"
        for name in ("blocking.blend", "blocking.py", "result.json", "blocking.blend1"):
            for junk in previs.glob(f"option_*/{name}"):
                junk.unlink()
        manifest = json.loads((previs / "previs.json").read_text(encoding="utf-8"))
        for entry in manifest["options"]:
            entry["files"] = [f for f in entry["files"] if f["role"] != "blend"]
        S.write_json(previs / "previs.json", manifest)
        shown = out.replace(str(folder), f"examples/{slug}")
        shown = "\n".join(line for line in shown.splitlines() if not line.strip().startswith("blend:")) + "\n"
        (folder / "transcript").mkdir(exist_ok=True)
        (folder / "transcript" / "previs.txt").write_text(shown, encoding="utf-8")
        (folder / "transcript" / "blender-detect.txt").write_text(text, encoding="utf-8")
        print(f"{slug}: {'ok' if code == 0 else 'FAILED'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
