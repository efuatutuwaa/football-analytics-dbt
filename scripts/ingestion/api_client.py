"""Shared API-Football client with rate-limit aware retries."""

import threading
import time
from typing import Optional

import requests

API_BASE_URL = "https://v3.football.api-sports.io"
DEFAULT_SLEEP_SECONDS = 0.5
MAX_RETRIES = 5
MIN_REMAINING_TO_STOP = 100
LOW_REMAINING_THRESHOLD = 50
LOW_REMAINING_SLEEP_SECONDS = 5.0

_requests_made = 0
_requests_lock = threading.Lock()


def get_requests_made() -> int:
    with _requests_lock:
        return _requests_made


def reset_requests_made() -> None:
    global _requests_made
    with _requests_lock:
        _requests_made = 0


def _increment_requests() -> None:
    global _requests_made
    with _requests_lock:
        _requests_made += 1


def _header_value(response: requests.Response, *names: str) -> Optional[str]:
    for name in names:
        value = response.headers.get(name)
        if value is not None:
            return value
    return None


def _wait_for_rate_limit(response: requests.Response, attempt: int) -> float:
    retry_after = _header_value(response, "Retry-After")
    if retry_after:
        try:
            return max(1.0, float(retry_after))
        except ValueError:
            pass

    reset_ts = _header_value(
        response,
        "x-ratelimit-requests-reset",
        "X-RateLimit-Requests-Reset",
    )
    if reset_ts:
        try:
            wait = float(reset_ts) - time.time()
            if wait > 0:
                return wait + 1.0
        except ValueError:
            pass

    return min(60.0, max(15.0, 2.0**attempt))


def _wait_for_server_error(attempt: int) -> float:
    return min(60.0, max(2.0, 2.0**attempt))


def _is_retryable_status(status_code: int) -> bool:
    return status_code == 429 or status_code >= 500


def _post_request_throttle(response: requests.Response) -> None:
    daily_remaining = _header_value(
        response,
        "x-ratelimit-requests-remaining",
        "X-RateLimit-Requests-Remaining",
    )
    daily_limit = _header_value(
        response,
        "x-ratelimit-requests-limit",
        "X-RateLimit-Requests-Limit",
    )
    minute_remaining = _header_value(response, "X-RateLimit-Remaining")
    minute_limit = _header_value(response, "X-RateLimit-Limit")

    print(
        f"  API daily remaining: {daily_remaining}/{daily_limit} | "
        f"per-minute remaining: {minute_remaining}/{minute_limit}"
    )

    if daily_remaining is not None and int(daily_remaining) < MIN_REMAINING_TO_STOP:
        raise RuntimeError("⚠️ Daily API request limit almost reached — stopping!")

    sleep_seconds = DEFAULT_SLEEP_SECONDS
    if daily_remaining is not None and int(daily_remaining) < LOW_REMAINING_THRESHOLD:
        sleep_seconds = LOW_REMAINING_SLEEP_SECONDS
    if minute_remaining is not None and int(minute_remaining) < 20:
        sleep_seconds = max(sleep_seconds, 15.0)
    elif minute_remaining is not None and int(minute_remaining) < 50:
        sleep_seconds = max(sleep_seconds, 5.0)

    time.sleep(sleep_seconds)


def fetch_from_api(
    endpoint: str,
    params: Optional[dict] = None,
    *,
    headers: dict,
    base_url: str = API_BASE_URL,
    semaphore: Optional[threading.Semaphore] = None,
) -> dict:
    """GET an API-Football endpoint with retry on 429/5xx and rate-limit headers."""
    params = params or {}
    url = f"{base_url}/{endpoint}"

    def _do_fetch() -> dict:
        response = None
        for attempt in range(MAX_RETRIES + 1):
            response = requests.get(url, headers=headers, params=params)
            if _is_retryable_status(response.status_code):
                if response.status_code == 429:
                    wait = _wait_for_rate_limit(response, attempt)
                    reason = "Rate limited (429)"
                else:
                    wait = _wait_for_server_error(attempt)
                    reason = f"Server error ({response.status_code})"
                print(
                    f"  {reason}. Waiting {wait:.0f}s "
                    f"(retry {attempt + 1}/{MAX_RETRIES})..."
                )
                if attempt >= MAX_RETRIES:
                    response.raise_for_status()
                time.sleep(wait)
                continue

            response.raise_for_status()
            _increment_requests()
            _post_request_throttle(response)
            return response.json()

        if response is not None:
            response.raise_for_status()
        raise RuntimeError("API request failed after retries")

    if semaphore is not None:
        with semaphore:
            return _do_fetch()
    return _do_fetch()
