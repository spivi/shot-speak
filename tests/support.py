"""Shared test helpers: the repository path, the real command line, and 2 fixtures."""

import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import shotspeak as S  # noqa: E402

PHRASE = "the bullet time thingy where the camera swishes around them mid-air"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def run(argv, environ=None):
    """Run the real command line. Returns (exit code, standard output, standard error)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = S.main(argv, environ=environ or {})
    return code, out.getvalue(), err.getvalue()
