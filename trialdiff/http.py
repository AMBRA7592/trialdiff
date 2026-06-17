from __future__ import annotations

import json
import random
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class HttpJsonError(RuntimeError):
    pass


def build_url(base_url: str, params: dict[str, Any] | None = None) -> str:
    if not params:
        return base_url
    clean_params = {key: value for key, value in params.items() if value is not None}
    if not clean_params:
        return base_url
    return f"{base_url}?{urlencode(clean_params, doseq=True)}"


RETRYABLE_HTTP_CODES = {429, 502, 503, 504}


def get_json(
    url: str,
    params: dict[str, Any] | None = None,
    timeout: float = 30.0,
    attempts: int = 5,
    base_delay: float = 1.0,
) -> Any:
    full_url = build_url(url, params)
    request = Request(full_url, headers={"Accept": "application/json", "User-Agent": "TrialDiff/0.1"})
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
            try:
                return json.loads(body)
            except json.JSONDecodeError as exc:
                raise HttpJsonError(f"Expected JSON from {full_url}") from exc
        except HTTPError as exc:
            last_error = RuntimeError(f"HTTP {exc.code}: {exc.reason}")
            exc.close()
            if exc.code not in RETRYABLE_HTTP_CODES or attempt == attempts - 1:
                break
            sleep_before_retry(attempt, base_delay)
        except URLError as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            sleep_before_retry(attempt, base_delay)
        except Exception as exc:  # pragma: no cover - platform-specific transport failures vary
            last_error = exc
            break
    raise HttpJsonError(f"Failed to fetch {full_url}: {last_error}") from last_error


def sleep_before_retry(attempt: int, base_delay: float) -> None:
    if base_delay <= 0:
        return
    delay = base_delay * (2**attempt) + random.uniform(0, base_delay)
    time.sleep(delay)
