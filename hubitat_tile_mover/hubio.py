# hubio.py - Hubitat dashboard layout import/export helpers (local LAN)
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Tuple

from .util import die, ilog, wlog, dlog

_REQUEST_TOKEN_RE = re.compile(r"javascriptRequestToken\s*=\s*['\"]([^'\"]+)['\"]")

@dataclass(frozen=True)
class HubUrls:
    dashboard_url: str
    layout_url: str
    request_token: str

def _read_url_text(url: str, *, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "hubitat_tile_mover/rc"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    return data.decode("utf-8", errors="replace")

def _build_layout_url(dashboard_url: str, request_token: str) -> str:
    u = urllib.parse.urlparse(dashboard_url)
    if not u.scheme or not u.netloc or not u.path:
        die("URL does not look valid. Use --url with a local dashboard URL.")
    host = u.hostname or ""
    if not host:
        die("URL does not look valid (missing host).")
    netloc = f"{host}:8080"
    path = u.path.rstrip("/") + "/layout"

    q = urllib.parse.parse_qsl(u.query, keep_blank_values=True)
    q2 = [(k, v) for (k, v) in q if not (k.lower() == "local" and v.lower() == "true")]
    q2.append(("requestToken", request_token))
    query = urllib.parse.urlencode(q2)

    return urllib.parse.urlunparse((u.scheme, netloc, path, "", query, ""))

def fetch_request_token(dashboard_url: str, *, verbose: bool = False, debug: bool = False) -> str:
    html = _read_url_text(dashboard_url)
    m = _REQUEST_TOKEN_RE.search(html)
    if not m:
        if debug or verbose:
            dlog(debug, f"dashboard html (first 400 chars): {html[:400]}")
        die("Could not find requestToken in the dashboard HTML. Make sure --url is a local dashboard URL.")
    token = m.group(1).strip()
    if not token:
        die("requestToken was found but empty.")
    return token

def hub_import_layout(dashboard_url: str, *, verbose: bool = False, debug: bool = False) -> Tuple[HubUrls, Any]:
    token = fetch_request_token(dashboard_url, verbose=verbose, debug=debug)
    layout_url = _build_layout_url(dashboard_url, token)
    if verbose:
        ilog(f"Hub import: layout URL = {layout_url}")
    text = _read_url_text(layout_url)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        if verbose or debug:
            dlog(debug, f"layout response (first 400 chars): {text[:400]}")
        die("Hub layout response was not valid JSON.")
    return HubUrls(dashboard_url=dashboard_url, layout_url=layout_url, request_token=token), obj

def _hub_post_once(layout_url: str, obj: Any, *, verbose: bool = False, debug: bool = False) -> None:
    data = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        layout_url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "hubitat_tile_mover/rc",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        resp.read()

def hub_post_layout_with_refresh(dashboard_url: str, last_layout_url: str, obj: Any, *, verbose: bool = False, debug: bool = False) -> str:
    try:
        _hub_post_once(last_layout_url, obj, verbose=verbose, debug=debug)
        return last_layout_url
    except Exception:
        if verbose:
            wlog("POST failed once; refreshed requestToken and retrying.")
        token = fetch_request_token(dashboard_url, verbose=verbose, debug=debug)
        new_layout_url = _build_layout_url(dashboard_url, token)
        _hub_post_once(new_layout_url, obj, verbose=verbose, debug=debug)
        return new_layout_url
