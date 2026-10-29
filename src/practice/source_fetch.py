# ABOUTME: Fetches raw upstream bytes over https (or loopback http), no redirects.
# ABOUTME: Downloaded bytes are only returned for storage and hashing, never executed.

import http.client
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import IO
from urllib.parse import quote, urlsplit

Fetcher = Callable[[str], bytes]

MAX_FETCH_BYTES = 5 * 1024 * 1024
FETCH_TIMEOUT_SECONDS = 30.0
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
GITHUB_RAW_HOST = "https://raw.githubusercontent.com"


class FetchError(Exception):
    """A URL could not be fetched safely; the message says why."""


class _RefuseRedirects(urllib.request.HTTPRedirectHandler):
    # A redirect would leave the exact URL we record as acquisition evidence.
    def redirect_request(  # type: ignore[no-untyped-def]
        self, req, fp, code, msg, headers, newurl
    ):
        raise FetchError(
            f"cannot fetch {req.full_url}: it answered with a redirect ({code}) to "
            f"{newurl}; redirects are not followed"
        )


def address_refusal(url: str) -> str | None:
    """Why this address may not be fetched, or None when it may."""
    parts = urlsplit(url)
    if parts.scheme == "https":
        return None
    if parts.scheme == "http" and parts.hostname in LOOPBACK_HOSTS:
        return None
    return "only https URLs (or http on a loopback address) are fetched"


def fetch_url(
    url: str,
    *,
    max_bytes: int = MAX_FETCH_BYTES,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> bytes:
    """GET the address, or POST `data` to it, and return the body.

    Only https (or http on a loopback address), no redirects, size-capped.
    """
    refusal = address_refusal(url)
    if refusal:
        raise FetchError(f"cannot fetch {url}: {refusal}")
    loopback = urlsplit(url).hostname in LOOPBACK_HOSTS
    handlers: list[urllib.request.BaseHandler] = [_RefuseRedirects()]
    if loopback:
        handlers.append(urllib.request.ProxyHandler({}))
    opener = urllib.request.build_opener(*handlers)
    request = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": "practice-sources", **(headers or {})},
    )
    try:
        with opener.open(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            return _read_limited(response, url, max_bytes)
    except urllib.error.HTTPError as error:
        error.close()
        raise FetchError(f"cannot fetch {url}: HTTP {error.code}") from error
    except (urllib.error.URLError, http.client.HTTPException, OSError) as error:
        raise FetchError(f"cannot fetch {url}: {error}") from error


def _read_limited(response: IO[bytes], url: str, max_bytes: int) -> bytes:
    body = response.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise FetchError(f"{url} is larger than the {max_bytes} byte limit")
    return body


def default_raw_base(repository: str) -> str:
    """The raw-content base for a GitHub repository URL such as https://github.com/o/r."""
    parts = urlsplit(repository)
    segments = [s for s in parts.path.split("/") if s]
    if parts.scheme != "https" or parts.hostname != "github.com" or len(segments) != 2:
        raise FetchError(
            f"cannot derive a raw download URL from {repository!r}; give a "
            "https://github.com/OWNER/REPO URL or an explicit raw base"
        )
    return f"{GITHUB_RAW_HOST}/{segments[0]}/{segments[1]}"


def raw_url(raw_base: str, revision: str, path: str) -> str:
    return f"{raw_base.rstrip('/')}/{revision}/{quote(path, safe='/')}"
