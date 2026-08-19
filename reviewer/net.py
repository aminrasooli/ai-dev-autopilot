"""Loopback-only HTTP for the local reviewer.

The ollama backend's privacy claim — local review stays local — is enforced
here, at the one door every request passes through, not by asking the
adapter to behave. A non-loopback URL raises ConfigError before any socket
is opened, and there is no code path that retries against a different host.
"""

import ipaddress
import json
import urllib.error
import urllib.parse
import urllib.request

from .errors import ConfigError, MalformedResponse, ReviewerUnavailable

LOCAL_HOSTNAMES = {"localhost", "localhost.localdomain"}


def is_local_url(url):
    """True only for http(s) URLs whose host is loopback."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname or ""
    if host.lower() in LOCAL_HOSTNAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def require_local(url):
    if not is_local_url(url):
        host = urllib.parse.urlparse(url).hostname
        raise ConfigError(
            f"reviewer endpoint must be loopback, got host {host!r}: "
            "local review stays local, and a remote endpoint would silently break that")


def post_json(url, payload, timeout, opener=None):
    """POST JSON to a loopback URL, return (status, parsed-body).

    `opener` exists for tests: anything with .open(request, timeout=) can
    stand in for the network. The loopback check runs before the opener is
    consulted, so a test double cannot bypass it either.
    """
    require_local(url)
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"})
    opener = opener or urllib.request.build_opener()
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", "replace")
            status = getattr(response, "status", 200)
    except urllib.error.HTTPError as exc:
        # An HTTP error still carries a body worth parsing: Ollama reports
        # "model not found" as a 404 with a JSON error field.
        body = exc.read().decode("utf-8", "replace")
        status = exc.code
    except OSError as exc:
        raise ReviewerUnavailable(f"cannot reach {url}: {exc}") from exc
    try:
        return status, json.loads(body)
    except ValueError as exc:
        raise MalformedResponse(
            f"{url} returned non-JSON (status {status}): {body[:200]!r}") from exc
