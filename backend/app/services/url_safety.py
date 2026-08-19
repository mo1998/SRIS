"""
Outbound URL safety guard (SSRF protection).

Validates that a URL is safe for the server to connect to on behalf of a user.
Rejects private/loopback/link-local/cloud-metadata targets (which would let an
org admin pivot to internal services or steal API keys), embedded credentials,
and non-http(s) schemes.

In production (DEBUG=False) only https is allowed; in development the well-known
local LLM endpoints (local-model, localhost, 127.0.0.1) are permitted so the
local vLLM container remains reachable.
"""

import ipaddress
import re
import socket
from typing import Optional
from urllib.parse import urlparse

from app.config import settings

# IP literals that must never be reachable from the backend.
_BLOCKED_NETWORKS = (
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)

# Hosts allowed to bypass the https-only rule in production. These are the
# Docker-internal model service hostnames that legitimately run over http.
_PRODUCTION_HTTP_ALLOWLIST = {"local-model", "localhost"}

_HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.?$")


def _ip_is_blocked(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    return any(ip in net for net in _BLOCKED_NETWORKS)


def _host_is_allowed_http(host: str) -> bool:
    """Hosts that may be reached over plain http even in production."""
    base = host.lower().rstrip(".")
    if base in _PRODUCTION_HTTP_ALLOWLIST:
        return True
    # Allow the local-model docker service with a service port, e.g. local-model:8100
    return bool(re.match(r"^local-model(:\d+)?$", base))


def validate_outbound_url(url: str, *, allow_http_local: bool = True) -> Optional[str]:
    """Validate a URL for an outbound server request.

    Returns an error message string if the URL is unsafe, otherwise None.

    - allow_http_local: permit plain-http to the well-known local model hosts in
      production; used for the LLM base URL so the Docker local-model works.
    """
    if not url:
        return None

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return "Only http/https URLs are allowed"

    if parsed.username or parsed.password:
        return "URLs must not contain embedded credentials"

    if not parsed.hostname:
        return "URL must include a hostname"

    host = parsed.hostname

    # Enforce https outside of development unless the host is explicitly allowlisted.
    if parsed.scheme != "https" and not settings.DEBUG and not (allow_http_local and _host_is_allowed_http(host)):
        return "Only https URLs are allowed in production"

    # If the host is an IP literal, check it directly.
    try:
        ip = ipaddress.ip_address(host)
        if _ip_is_blocked(str(ip)):
            return "URL points to a private or blocked address"
    except ValueError:
        pass  # hostname, resolve below

    # Resolve the hostname and reject any resolved address in a blocked range.
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
        resolved = {info[4][0] for info in infos}
    except socket.gaierror:
        # Unresolvable host; leave resolution to connection time rather than
        # hard-blocking (DNS may be transiently unavailable).
        return None

    for addr in resolved:
        if _ip_is_blocked(addr):
            return "URL resolves to a private or blocked address"

    return None
