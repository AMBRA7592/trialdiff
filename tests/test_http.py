from __future__ import annotations

from urllib.error import HTTPError
import unittest
from unittest.mock import patch

from trialdiff.http import HttpJsonError, get_json


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return self.body


def http_error(code: int) -> HTTPError:
    return HTTPError("https://example.test", code, "error", hdrs=None, fp=None)


class HttpTests(unittest.TestCase):
    def test_get_json_retries_retryable_http_errors(self) -> None:
        calls = {"count": 0}

        def fake_urlopen(_request, timeout):
            calls["count"] += 1
            if calls["count"] < 3:
                raise http_error(503)
            return FakeResponse(b'{"ok": true}')

        with patch("trialdiff.http.urlopen", side_effect=fake_urlopen):
            result = get_json("https://example.test", attempts=5, base_delay=0)

        self.assertEqual(result, {"ok": True})
        self.assertEqual(calls["count"], 3)

    def test_get_json_does_not_retry_non_retryable_http_errors(self) -> None:
        with patch("trialdiff.http.urlopen", side_effect=http_error(404)) as mocked:
            with self.assertRaises(HttpJsonError):
                get_json("https://example.test", attempts=5, base_delay=0)

        self.assertEqual(mocked.call_count, 1)


if __name__ == "__main__":
    unittest.main()
