import httpx, time
from dataclasses import dataclass

DEFAULT_HEADERS = {"User-Agent": "centaur/0.2 (public-osint-ingest)"}

@dataclass
class HttpCacheEntry:
    etag: str | None = None
    last_modified: str | None = None

_cache: dict[str, HttpCacheEntry] = {}

def get_client(timeout: float = 30.0):
    return httpx.Client(timeout=timeout, headers=DEFAULT_HEADERS, follow_redirects=True)

def get_with_retry(
    url: str,
    client: httpx.Client,
    max_tries: int = 4,
    extra_headers: dict[str, str] | None = None,
) -> httpx.Response:
    delay = 1.0
    headers = {}
    if url in _cache:
        if _cache[url].etag: headers["If-None-Match"] = _cache[url].etag
        if _cache[url].last_modified: headers["If-Modified-Since"] = _cache[url].last_modified
    if extra_headers:
        headers.update(extra_headers)

    last_exc = None
    max_delay = 60.0
    for _ in range(max_tries):
        try:
            r = client.get(url, headers=headers)
            if r.status_code == 304:
                return r
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(delay)
                delay = min(delay * 2, max_delay)
                continue
            etag = r.headers.get("ETag")
            lm = r.headers.get("Last-Modified")
            if etag or lm:
                _cache[url] = HttpCacheEntry(etag=etag, last_modified=lm)
            return r
        except Exception as e:
            last_exc = e
            time.sleep(delay)
            delay = min(delay * 2, max_delay)
    if last_exc is None:
        err_msg = "no response (timeout or connection error)"
    else:
        name = type(last_exc).__name__
        detail = str(last_exc).strip() or repr(last_exc).strip()
        if not detail or detail.lower() == "unknown":
            detail = "connection or SSL failed"
        err_msg = f"{name}: {detail}"
    raise RuntimeError(f"GET failed after retries: {url} ({err_msg})")
