"""
Security helpers for WebTools: URL validation (SSRF), safe paths, response limits.
"""

from __future__ import annotations

import ipaddress
import os
import socket
from pathlib import Path
from typing import Optional, Set, Tuple
from urllib.parse import urlparse

# Schemes allowed for outbound HTTP(S) fetches
ALLOWED_SCHEMES = frozenset({"http", "https"})

# Hard caps to avoid DoS / memory blowups
DEFAULT_MAX_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MiB
DEFAULT_MAX_REDIRECTS = 5
DEFAULT_TIMEOUT = 10
DEFAULT_MAX_CRAWL_PAGES = 50
DEFAULT_MAX_CRAWL_DEPTH = 3
DEFAULT_MAX_BROKEN_LINK_CHECKS = 100

# Hostnames treated as loopback / local regardless of DNS
BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "ip6-localhost",
        "ip6-loopback",
        "metadata.google.internal",
        "metadata",
    }
)


class SecurityError(ValueError):
    """Raised when a URL or path fails security checks."""


def _is_private_or_reserved(ip: ipaddress._BaseAddress) -> bool:
    """Return True if the IP must not be contacted (SSRF)."""
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        or (ip.version == 4 and ip in ipaddress.ip_network("169.254.0.0/16"))
        or (ip.version == 6 and ip in ipaddress.ip_network("fc00::/7"))
    )


def _hostname_is_blocked(hostname: str) -> bool:
    host = hostname.lower().rstrip(".")
    if host in BLOCKED_HOSTNAMES:
        return True
    # Trailing/leading dots and empty
    if not host:
        return True
    # Literal IPv4/IPv6 in hostname
    try:
        ip = ipaddress.ip_address(host.strip("[]"))
        return _is_private_or_reserved(ip)
    except ValueError:
        pass
    return False


def resolve_and_validate_host(hostname: str) -> None:
    """
    Resolve hostname and reject private/reserved addresses (SSRF guard).
    Raises SecurityError if unsafe.
    """
    if _hostname_is_blocked(hostname):
        raise SecurityError(f"Blocked host: {hostname}")

    host = hostname.strip("[]")
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise SecurityError(f"Cannot resolve host: {hostname} ({e})") from e

    if not infos:
        raise SecurityError(f"Cannot resolve host: {hostname}")

    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if _is_private_or_reserved(ip):
            raise SecurityError(
                f"Host resolves to blocked address {addr}: {hostname}"
            )


def validate_url(
    url: str,
    *,
    allow_http: bool = True,
    resolve_dns: bool = True,
) -> str:
    """
    Validate a URL for safe outbound requests.
    Returns the normalized URL string or raises SecurityError.
    """
    if not url or not isinstance(url, str):
        raise SecurityError("URL must be a non-empty string")

    url = url.strip()
    parsed = urlparse(url)

    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        raise SecurityError(
            f"Disallowed URL scheme '{scheme or '(none)'}'. "
            f"Only {', '.join(sorted(ALLOWED_SCHEMES))} are allowed."
        )

    if scheme == "http" and not allow_http:
        raise SecurityError("HTTP URLs are disabled; use HTTPS")

    hostname = parsed.hostname
    if not hostname:
        raise SecurityError("URL missing hostname")

    # Block credentials in URL (user:pass@host) to avoid accidental leak / abuse
    if parsed.username or parsed.password:
        raise SecurityError("URLs with embedded credentials are not allowed")

    if resolve_dns:
        resolve_and_validate_host(hostname)
    elif _hostname_is_blocked(hostname):
        raise SecurityError(f"Blocked host: {hostname}")

    return url


def safe_output_path(
    filename: str,
    *,
    base_dir: Optional[str] = None,
    allowed_suffixes: Optional[Set[str]] = None,
) -> Path:
    """
    Resolve a write/read path under base_dir (default: cwd).
    Rejects path traversal and absolute paths outside the base.
    """
    if not filename or not isinstance(filename, str):
        raise SecurityError("Filename must be a non-empty string")

    # Reject null bytes
    if "\x00" in filename:
        raise SecurityError("Filename contains null byte")

    base = Path(base_dir or os.getcwd()).resolve()
    candidate = Path(filename)

    # Disallow absolute paths that escape base
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (base / candidate).resolve()

    try:
        resolved.relative_to(base)
    except ValueError as e:
        raise SecurityError(
            f"Path escapes working directory: {filename}"
        ) from e

    if allowed_suffixes is not None:
        suffix = resolved.suffix.lower()
        if suffix not in allowed_suffixes:
            raise SecurityError(
                f"Disallowed file extension '{suffix}'. "
                f"Allowed: {', '.join(sorted(allowed_suffixes))}"
            )

    return resolved


def safe_write_text(filename: str, content: str, encoding: str = "utf-8") -> Path:
    """Write text to a path confined to the current working directory."""
    path = safe_output_path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding=encoding)
    return path


def safe_write_json(filename: str, data, indent: int = 2) -> Path:
    """Write JSON to a path confined to the current working directory."""
    import json

    path = safe_output_path(
        filename,
        allowed_suffixes={".json", ".txt", ".md", ".csv", ".xml", ".html", ".log"},
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
    return path


def safe_read_json(filename: str):
    """Read JSON from a path confined to the current working directory."""
    import json

    path = safe_output_path(filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_read_text(filename: str) -> str:
    """Read text from a path confined to the current working directory."""
    path = safe_output_path(filename)
    return path.read_text(encoding="utf-8")


def create_safe_session(
    requests_module,
    *,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
    user_agent: str = "WebTools/1.0 (+security; research)",
):
    """
    Build a requests.Session with redirect SSRF re-validation.
    Each redirect target is re-checked with validate_url.
    """
    session = requests_module.Session()
    session.headers.update({"User-Agent": user_agent})
    session.max_redirects = max_redirects

    # Hook: validate every redirect Location before following
    def _ssrf_redirect_hook(response, *args, **kwargs):
        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get("Location")
            if location:
                from urllib.parse import urljoin

                next_url = urljoin(response.url, location)
                validate_url(next_url)
        return response

    session.hooks["response"].append(_ssrf_redirect_hook)
    return session


def safe_get(
    session,
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    max_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    allow_http: bool = True,
    **kwargs,
) -> Tuple[object, bytes]:
    """
    GET with URL validation and response size limit.
    Returns (response, content_bytes). Raises SecurityError / RequestException.
    """
    validate_url(url, allow_http=allow_http)
    # stream=True so we can cap download size
    response = session.get(url, timeout=timeout, stream=True, **kwargs)
    response.raise_for_status()

    chunks = []
    total = 0
    for chunk in response.iter_content(chunk_size=65536):
        if not chunk:
            continue
        total += len(chunk)
        if total > max_bytes:
            response.close()
            raise SecurityError(
                f"Response exceeds size limit ({max_bytes} bytes)"
            )
        chunks.append(chunk)

    content = b"".join(chunks)
    # Attach decoded text convenience without re-downloading
    response._content = content
    return response, content


def is_sensitive_field_name(name: str) -> bool:
    """Heuristic: treat field as secret so we do not log its value."""
    if not name:
        return False
    lowered = name.lower()
    secrets = (
        "pass",
        "passwd",
        "password",
        "secret",
        "token",
        "api_key",
        "apikey",
        "auth",
        "credential",
        "private",
        "ssn",
        "cvv",
        "card",
    )
    return any(s in lowered for s in secrets)


def redact_value(name: str, value: str) -> str:
    """Redact value when field name looks sensitive."""
    if is_sensitive_field_name(name):
        return "***REDACTED***"
    if value and len(value) > 80:
        return value[:40] + "…(truncated)"
    return value
