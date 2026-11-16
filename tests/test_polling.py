"""Offline tests for provider status checks, redirects and the approval of the estimate. No test reaches the network."""

import io
import json
import sys
import tempfile
import unittest
import urllib.request
from email.message import Message
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import shotspeak as S  # noqa: E402
from support import PHRASE, PNG, run  # noqa: E402

CREATE = "https://api.replicate.com/v1/models/owner/model/predictions"
STATUS = "https://api.replicate.com/v1/predictions/p1"


class Offline(unittest.TestCase):
    def setUp(self):
        self._urlopen, self._open = urllib.request.urlopen, urllib.request.OpenerDirector.open

        def bomb(*args, **kwargs):
            raise AssertionError("A test tried to reach the network.")

        urllib.request.urlopen = bomb
        urllib.request.OpenerDirector.open = bomb
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        urllib.request.urlopen, urllib.request.OpenerDirector.open = self._urlopen, self._open
        self.tmp.cleanup()

    def base(self, *extra):
        return ["--cwd", str(self.dir), *extra]


class ReplicateStatusChecks(Offline):
    def replicate(self, status_link, answers=None, **kw):
        calls = []
        answers = list(answers or [])

        def transport(method, url, headers, body=None, timeout=180):
            calls.append((method, url, headers))
            if method == "POST":
                return 201, json.dumps({"id": "p1", "status": "starting", "urls": {"get": status_link}}).encode()
            if url.startswith("https://cdn."):
                return 200, PNG
            return 200, json.dumps(answers.pop(0) if answers else {"id": "p1", "status": "processing", "urls": {"get": status_link}}).encode()

        try:
            return S.gen_replicate("a prompt", {"model": "owner/model"}, "r8_k", "", "", {}, transport, sleep=lambda s: None, **kw), calls
        except S.ProviderError as exc:
            return exc, calls

    def test_a_status_link_on_the_same_https_host_is_checked_with_the_key(self):
        done = {"id": "p1", "status": "succeeded", "output": ["https://cdn.example.org/a.png"]}
        (image, extra), calls = self.replicate(STATUS, [done])
        self.assertEqual(image, PNG)
        self.assertEqual([c[1] for c in calls], [CREATE, STATUS, "https://cdn.example.org/a.png"])
        self.assertEqual(calls[1][2]["Authorization"], "Bearer r8_k")
        self.assertNotIn("Authorization", calls[2][2])

    def test_a_status_link_on_another_host_or_scheme_is_never_opened(self):
        for link in ("https://other.example.org/v1/predictions/p1", "http://api.replicate.com/v1/predictions/p1",
                     "https://api.replicate.com.evil.example/p1", "file:///etc/passwd", ""):
            exc, calls = self.replicate(link)
            self.assertIsInstance(exc, S.ProviderError, link)
            self.assertTrue(exc.ambiguous, link)
            self.assertEqual([c[0] for c in calls], ["POST"], link)  # created once, nothing else sent

    def test_the_checks_stop_at_the_count_and_the_time_limit(self):
        exc, calls = self.replicate(STATUS, max_polls=3)
        self.assertTrue(exc.ambiguous)
        self.assertEqual([c[0] for c in calls], ["POST", "GET", "GET", "GET"])
        ticks = iter(range(0, 1000, 100))
        exc, calls = self.replicate(STATUS, max_seconds=250, clock=lambda: next(ticks))
        self.assertTrue(exc.ambiguous)
        self.assertEqual(sum(1 for c in calls if c[0] == "POST"), 1)
        self.assertLessEqual(len(calls), 4)

    def test_a_failed_prediction_is_a_rejection(self):
        exc, _ = self.replicate(STATUS, [{"id": "p1", "status": "failed", "error": "bad input"}])
        self.assertFalse(exc.ambiguous)


class Redirects(Offline):
    def redirect(self, start, target):
        handler = S._RedirectHandler()
        request = urllib.request.Request(start, headers={"Authorization": "Bearer secret", "Content-Type": "application/json"})
        return handler.redirect_request(request, io.BytesIO(), 302, "Found", Message(), target)

    def test_a_redirect_on_the_same_host_keeps_the_key(self):
        new = self.redirect("https://api.example.org/a", "https://api.example.org/b")
        self.assertEqual(new.get_header("Authorization"), "Bearer secret")

    def test_a_redirect_to_another_host_gets_no_key(self):
        new = self.redirect("https://api.example.org/a", "https://cdn.example.org/b")
        self.assertIsNone(new.get_header("Authorization"))
        self.assertEqual(new.full_url, "https://cdn.example.org/b")

    def test_a_redirect_that_is_not_https_is_not_followed(self):
        with self.assertRaises(S.ProviderError) as caught:
            self.redirect("https://api.example.org/a", "http://api.example.org/b")
        self.assertTrue(caught.exception.ambiguous)

    def test_the_transport_uses_the_redirect_rules(self):
        self.assertTrue(any(isinstance(h, S._RedirectHandler) for h in S._opener().handlers))


class EstimateIsPartOfTheApproval(Offline):
    def test_a_changed_estimate_changes_the_fingerprint(self):
        backend = {"name": "fal", "model": "owner/model"}
        cheap = S.request_fingerprint(backend, "1536x864", "medium", ["p"], {"SHOTSPEAK_EST_USD_PER_IMAGE": ("0.01", "t")})
        dear = S.request_fingerprint(backend, "1536x864", "medium", ["p"], {"SHOTSPEAK_EST_USD_PER_IMAGE": ("0.20", "t")})
        unknown = S.request_fingerprint(backend, "1536x864", "medium", ["p"], {})
        self.assertEqual(len({cheap, dear, unknown}), 3)

    def test_a_yes_for_one_estimate_is_refused_for_another(self):
        out = self.dir / "o"
        run(self.base("plan", "--phrase", PHRASE, "--out", str(out)))
        env = {"FAL_KEY": "fal_secret_value_123456", "SHOTSPEAK_FAL_MODEL": "owner/model", "SHOTSPEAK_EST_USD_PER_IMAGE": "0.01"}
        _, text, _ = run(self.base("mock", "--options", str(out / "options.json"), "--dry-run"), env)
        self.assertIn("Estimate:  0.04 USD", text)
        fingerprint = text.split("--confirm ")[-1].split()[0]
        env["SHOTSPEAK_EST_USD_PER_IMAGE"] = "0.05"
        code, _, err = run(self.base("mock", "--options", str(out / "options.json"), "--confirm", fingerprint), env)
        self.assertEqual(code, 2)
        self.assertIn("does not match this card", err)

    def test_the_count_is_part_of_the_approval(self):
        backend = {"name": "openai", "model": S.OPENAI_DEFAULT_MODEL}
        self.assertNotEqual(S.request_fingerprint(backend, "1536x864", "medium", ["a", "b"], {}),
                            S.request_fingerprint(backend, "1536x864", "medium", ["a", "b", "c"], {}))


if __name__ == "__main__":
    unittest.main()
