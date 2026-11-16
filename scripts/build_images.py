#!/usr/bin/env python3
"""Make the comparison images of the README: a paid request, sent only after a clear yes.

    python3 scripts/build_images.py --dry-run             # print the prompts, the model, the size, the estimate
    python3 scripts/build_images.py --confirm FINGERPRINT # generate the images that are still placeholders
    python3 scripts/build_images.py --convert-existing    # make committed JPEG files from PNG files in docs/img; sends nothing

For each example scene it makes 3 images: the first prompt as typed, the clear prompt with no film language,
and the mock still of the shot-speak result. It also makes the 4 option stills of the main session.
Every image goes to a fixed path in ``docs/img/``. An image that exists is not requested again (--force).
One request for each image. No automatic retry. Python 3 standard library only.

The provider returns a large PNG. The repository keeps a small JPEG: 1280x720, no metadata. The conversion
needs the ``ffmpeg`` program. The same PNG gives the same JPEG bytes with the same ffmpeg version.
``receipts.json`` keeps the SHA-256 of the provider's PNG (``image_sha256``) and of the committed file (``file_sha256``).
The PNG files go to ``shotspeak_out/comparison_originals/``, which Git ignores.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_walkthrough as W  # noqa: E402
import shotspeak as S  # noqa: E402

JPEG_SIZE = "1280:720"
JPEG_QUALITY = "3"  # the ffmpeg scale 2 to 31: 3 is about quality 85
ORIGINALS = W.ROOT / "shotspeak_out" / "comparison_originals"


def to_jpeg(png):
    """PNG bytes in, JPEG bytes out: 1280x720, no metadata."""
    program = shutil.which("ffmpeg")
    if not program:
        raise S.Refusal("The conversion to JPEG needs the ffmpeg program. Install it, then run again.")
    with tempfile.TemporaryDirectory() as tmp:
        source, target = Path(tmp) / "in.png", Path(tmp) / "out.jpg"
        source.write_bytes(png)
        done = subprocess.run([program, "-v", "error", "-y", "-i", str(source), "-vf", f"scale={JPEG_SIZE}:flags=lanczos",
                               "-q:v", JPEG_QUALITY, "-map_metadata", "-1", "-bitexact", "-pix_fmt", "yuvj420p", str(target)],
                              capture_output=True, text=True, timeout=120)
        if done.returncode != 0 or not target.is_file():
            raise S.Refusal("ffmpeg did not convert the image: " + (done.stderr or "").strip()[-200:])
        return target.read_bytes()


def keep_original(name, png):
    ORIGINALS.mkdir(parents=True, exist_ok=True)
    (ORIGINALS / (Path(name).stem + ".png")).write_bytes(png)


def convert_existing():
    """Turn each PNG in docs/img into the committed JPEG. No request. The receipts get the hash of the new file."""
    folder = W.DOCS / "img"
    path = folder / "receipts.json"
    receipts = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
    done = 0
    for source in sorted(folder.glob("*.png")):
        png = source.read_bytes()
        original = hashlib.sha256(png).hexdigest()
        receipt = next((r for r in receipts if Path(r.get("file", "")).stem == source.stem), None)
        if receipt and receipt.get("image_sha256") not in (None, original):
            raise S.Refusal(f"{source.name} is not the file of its receipt. It was not converted.")
        jpeg = to_jpeg(png)
        target = folder / (source.stem + ".jpg")
        keep_original(source.name, png)
        target.write_bytes(jpeg)
        source.unlink()
        if receipt:
            receipt.update({"file": target.name, "file_sha256": hashlib.sha256(jpeg).hexdigest(), "file_bytes": len(jpeg),
                            "file_format": f"JPEG {JPEG_SIZE.replace(':', 'x')}, no metadata; image_sha256 is the provider's PNG"})
        done += 1
        print(f"{source.name} -> {target.name}  {len(png)} -> {len(jpeg)} bytes")
    if receipts:
        S.write_json(path, receipts, ensure_ascii=True)
    print(f"{done} files converted. The PNG files are in {ORIGINALS.relative_to(W.ROOT)} (ignored by Git).")
    return 0


FRAME = "A single still frame from this video, 16:9: "
DEFAULT_MAX_USD = 1.50


def jobs():
    """[(file name, prompt, what it is)] in a fixed order."""
    out = []
    for slug in W.TIER_SCENES:
        tiers = W.load(f"{slug}/tiers.json")
        out.append((f"{slug}_bad.jpg", FRAME + tiers["bad"]["prompt"], "the first prompt, as typed"))
        out.append((f"{slug}_plain.jpg", FRAME + tiers["plain"]["prompt"], "the clear prompt, no film language"))
        out.append((f"{slug}_skill.jpg", tiers["skill"]["image_prompt"], "the shot-speak mock still"))
    for option in W.load(f"{W.MAIN}/options.json")["options"]:
        out.append((f"{W.MAIN}_option_{option['label']}.jpg", option["image_prompt"], f"option {option['label']} of the main session"))
    return out


def main(argv=None, environ=None, transport=None):
    parser = argparse.ArgumentParser(description="Make the README comparison images.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", metavar="FINGERPRINT")
    parser.add_argument("--backend", default="openai")
    parser.add_argument("--model")
    parser.add_argument("--size", default="1536x864")
    parser.add_argument("--quality", default="medium", choices=S.QUALITIES)
    parser.add_argument("--max-usd", type=float, default=DEFAULT_MAX_USD)
    parser.add_argument("--force", action="store_true", help="Also request images that exist.")
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--convert-existing", action="store_true", help="Convert PNG files in docs/img to JPEG. Sends nothing.")
    args = parser.parse_args(argv)
    env = S.load_env(args.cwd, None, environ)
    try:
        if args.convert_existing:
            return convert_existing()
        backend = S.select_backend(env, args.backend, args.model, require_key=bool(args.confirm))
        todo = [j for j in jobs() if args.force or W.is_placeholder(W.DOCS / "img" / j[0])]
        for name, prompt, _what in todo:
            problems = S.lint_prompt(prompt)
            if problems:
                raise S.Refusal(f"{name}: the prompt {problems[0]}")
        total, basis = S.estimate(backend, len(todo), env)
        payload = json.dumps([backend["name"], backend["model"], args.size, args.quality, [j[1] for j in todo]], sort_keys=True)
        fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
        for name, prompt, what in todo:
            print(f"--- docs/img/{name}  ({what})")
            print(prompt)
            print()
        cost = "unknown" if total is None else f"{total:.2f} USD"
        print(f"Backend:   {backend['name']}  (model {backend['model']})")
        print(f"Size:      {args.size}   Quality: {args.quality}")
        print(f"Images:    {len(todo)} to make, {len(jobs()) - len(todo)} exist")
        print(f"Estimate:  {cost}")
        print(f"Basis:     {basis}")
        print(f"Card:      {fingerprint}")
        if not todo:
            print("Every image exists. Nothing to do.")
            return 0
        if not args.confirm:
            print(f"\nNOT SENT. This is a paid request. After a clear yes, run again with --confirm {fingerprint}")
            return 0 if args.dry_run else 2
        if args.confirm != fingerprint:
            raise S.Refusal(f"--confirm does not match this card ({fingerprint}).")
        if total is None:
            raise S.Refusal("The cost is unknown. " + basis)
        if total > args.max_usd:
            raise S.Refusal(f"The estimate of {total:.2f} USD is above the limit of {args.max_usd:.2f} USD (--max-usd).")
        if backend["name"] == "openai":
            S.validate_size(args.size)
        key, secrets, receipts = env[backend["key_var"]][0], S.secrets_of(env), []
        for name, prompt, _what in todo:
            try:
                image, extra = S.GENERATORS[backend["name"]](prompt, backend, key, args.size, args.quality, env, transport or S.http_transport)
            except S.ProviderError as exc:
                status = "ambiguous" if exc.ambiguous else "rejected"
                receipts.append({"file": name, "status": status, "error": S.redact(exc, secrets)})
                print(S.redact(f"{name}: {status}. {exc}", secrets), file=sys.stderr)
                print("Stopped. Nothing was sent again. Check the provider's usage page before a new request.", file=sys.stderr)
                break
            jpeg = to_jpeg(image)
            keep_original(name, image)
            (W.DOCS / "img" / name).write_bytes(jpeg)
            receipts.append({"file": name, "status": "ok", "image_sha256": hashlib.sha256(image).hexdigest(),
                             "file_sha256": hashlib.sha256(jpeg).hexdigest(), "file_bytes": len(jpeg),
                             "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(), **extra})
            print(f"saved docs/img/{name}", file=sys.stderr)
        S.write_json(W.DOCS / "img" / "receipts.json", receipts, ensure_ascii=True)
        done = sum(1 for r in receipts if r["status"] == "ok")
        print(f"\n{done} of {len(todo)} images are in docs/img. Run scripts/build_walkthrough.py next.")
        return 0 if done == len(todo) else 1
    except S.Refusal as exc:
        print(S.redact(f"REFUSED: {exc}", S.secrets_of(env)), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
