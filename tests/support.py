"""Shared test helpers: the repository path, the real command line, and 2 fixtures."""

import io
import sys
import zlib
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import shotspeak as S  # noqa: E402

PHRASE = "the bullet time thingy where the camera swishes around them mid-air"


def _png_1x1():
    """A complete 1x1 grey PNG: the tool refuses a file that is not 1 whole image."""
    def chunk(kind, data):
        return len(data).to_bytes(4, "big") + kind + data + zlib.crc32(kind + data).to_bytes(4, "big")
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", (1).to_bytes(4, "big") * 2 + b"\x08\x00\x00\x00\x00")
            + chunk(b"IDAT", zlib.compress(b"\x00\x80")) + chunk(b"IEND", b""))


PNG = _png_1x1()


def run(argv, environ=None):
    """Run the real command line. Returns (exit code, standard output, standard error)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = S.main(argv, environ=environ or {})
    return code, out.getvalue(), err.getvalue()
