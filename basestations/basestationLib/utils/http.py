# ----------------------------
# No-proxy robust HTTP for WFS/API
# ----------------------------
import time
import random
import math
from typing import Optional, Dict, Any, Iterable, Tuple, List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ----------------------------
# Session
# ----------------------------
DEFAULT_HEADERS = {
    # A normal browser UA reduces some naive blocking
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9,nl;q=0.8",
    "Connection": "keep-alive",
}

RETRY_STATUSES = {429, 500, 502, 503, 504}
# For some servers, 403 is not transient; we typically do NOT hammer retries.
# But if you occasionally see transient 403 due to WAF/rate limit, you can include it.
RETRY_403 = False


def create_session(retries: int = 3, pool_maxsize: int = 64, headers: Optional[dict] = None) -> requests.Session:
    """
    Create a requests session with connection pooling + urllib3 retry for network-level issues.
    No proxies.
    """
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    if headers:
        session.headers.update(headers)

    retry_strategy = Retry(
        total=retries,
        status_forcelist=list(RETRY_STATUSES),
        allowed_methods=["GET"],
        backoff_factor=0.2,          # mild; we do our own backoff too
        raise_on_status=False,
        respect_retry_after_header=True,
    )

    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=pool_maxsize,
        pool_maxsize=pool_maxsize,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    print(f"Created HTTP session: retries={retries}, pool_maxsize={pool_maxsize}")
    return session


# ----------------------------
# Rate limiting (simple)
# ----------------------------
class RateLimiter:
    """
    Simple global rate limiter: ensures at most `rps` requests per second.
    """
    def __init__(self, rps: float = 2.0):
        self.rps = float(rps)
        self.min_interval = 1.0 / self.rps if self.rps > 0 else 0.0
        self._t_last = 0.0

    def wait(self):
        if self.min_interval <= 0:
            return
        now = time.time()
        dt = now - self._t_last
        if dt < self.min_interval:
            time.sleep(self.min_interval - dt)
        self._t_last = time.time()


# ----------------------------
# Robust GET with backoff + jitter
# ----------------------------
def _sleep_backoff(attempt: int, base: float = 0.6, cap: float = 20.0):
    """
    Exponential backoff with jitter.
    attempt=1 -> ~0.6s, attempt=2 -> ~1.2s, attempt=3 -> ~2.4s ...
    """
    delay = min(cap, base * (2 ** (attempt - 1)))
    # full jitter
    time.sleep(random.random() * delay)


def _retry_after_seconds(resp: requests.Response) -> Optional[float]:
    ra = resp.headers.get("Retry-After")
    if not ra:
        return None
    try:
        return float(ra)
    except ValueError:
        return None


def http_get(
    session: requests.Session,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    timeout: Tuple[float, float] = (5.0, 25.0),  # (connect, read)
    max_attempts: int = 6,
    rate_limiter: Optional[RateLimiter] = None,
    extra_headers: Optional[Dict[str, str]] = None,
) -> Optional[requests.Response]:
    """
    GET with:
      - optional global rate limit
      - retries on transient statuses + network errors
      - exponential backoff + jitter
      - respects Retry-After for 429
    """
    for attempt in range(1, max_attempts + 1):
        try:
            if rate_limiter:
                rate_limiter.wait()

            hdrs = None
            if extra_headers:
                hdrs = dict(session.headers)
                hdrs.update(extra_headers)

            resp = session.get(url, params=params, timeout=timeout, headers=hdrs)

            if resp.status_code == 200:
                
                return resp
            print(resp.text)
            # Decide retry
            retryable = (resp.status_code in RETRY_STATUSES) or (RETRY_403 and resp.status_code == 403)
            if not retryable:
                # don’t keep hammering if it’s a hard block or bad request
                return resp

            # If 429 and Retry-After is provided, honor it
            ra = _retry_after_seconds(resp)
            if ra is not None and ra > 0:
                time.sleep(min(60.0, ra))
            else:
                _sleep_backoff(attempt)

        except (requests.exceptions.ConnectTimeout,
                requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.SSLError):
            _sleep_backoff(attempt)
        except Exception:
            # unknown error; don’t spin forever
            return None

    return None


def http_get_json(
    session: requests.Session,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    timeout: Tuple[float, float] = (5.0, 25.0),
    max_attempts: int = 6,
    rate_limiter: Optional[RateLimiter] = None,
    extra_headers: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, Any]]:
    resp = http_get(
        session, url,
        params=params,
        timeout=timeout,
        max_attempts=max_attempts,
        rate_limiter=rate_limiter,
        extra_headers=extra_headers,
    )
    if resp is None:
        return None
    if resp.status_code != 200:
        return None
    try:
        return resp.json()
    except Exception:
        return None


def http_get_text(
    session: requests.Session,
    url: str,
    *,
    timeout: Tuple[float, float] = (5.0, 25.0),
    max_attempts: int = 6,
    rate_limiter: Optional[RateLimiter] = None,
    extra_headers: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    resp = http_get(
        session, url,
        timeout=timeout,
        max_attempts=max_attempts,
        rate_limiter=rate_limiter,
        extra_headers=extra_headers,
    )
    if resp is None:
        return None
    if resp.status_code != 200:
        return None
    return resp.text