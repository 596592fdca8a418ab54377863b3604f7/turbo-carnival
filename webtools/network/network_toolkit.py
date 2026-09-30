#!/usr/bin/env python3
"""
Network Toolkit - terminal network diagnostics (DNS, HTTP, TLS, connectivity).

Defensive / developer diagnostics only: inspect public hosts you are authorized
to test. Not a scanner or exploit framework.
"""

from __future__ import annotations

import json
import socket
import ssl
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# Allow running as script or via package path
try:
    from utils.security import (
        SecurityError,
        create_safe_session,
        resolve_and_validate_host,
        safe_write_json,
        validate_url,
    )
except ImportError:
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from utils.security import (
        SecurityError,
        create_safe_session,
        resolve_and_validate_host,
        safe_write_json,
        validate_url,
    )


# Common well-known service ports for named checks (not a scan range)
WELL_KNOWN_PORTS = {
    "http": 80,
    "https": 443,
    "ssh": 22,
    "ftp": 21,
    "smtp": 25,
    "dns": 53,
    "pop3": 110,
    "imap": 143,
    "ldap": 389,
    "smtps": 465,
    "imaps": 993,
    "pop3s": 995,
    "mysql": 3306,
    "postgres": 5432,
    "redis": 6379,
    "mongodb": 27017,
}

MAX_CONNECT_TIMEOUT = 5
MAX_HTTP_BODY_PREVIEW = 2048


class NetworkToolkit:
    """Network diagnostics for authorized public targets."""

    def __init__(self):
        try:
            import requests

            self.requests = requests
            self.session = create_safe_session(
                requests, user_agent="WebTools-Network/1.1 (+diagnostics)"
            )
        except ImportError as e:
            print(f"✗ Error: Required library not installed: {e}")
            print("Install with: pip install requests")
            sys.exit(1)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _normalize_host(self, target: str) -> str:
        """Extract hostname from URL or bare host; validate SSRF."""
        target = (target or "").strip()
        if not target:
            raise SecurityError("Host/URL must be a non-empty string")

        if "://" in target:
            parsed = urlparse(target)
            host = parsed.hostname
            if not host:
                raise SecurityError("URL missing hostname")
            resolve_and_validate_host(host)
            return host

        # Strip optional port for validation of hostname part
        host = target
        if host.startswith("["):
            # [ipv6]:port
            end = host.find("]")
            if end == -1:
                raise SecurityError("Invalid IPv6 host")
            host_only = host[1:end]
            resolve_and_validate_host(host_only)
            return host_only

        if ":" in host and host.count(":") == 1:
            host = host.split(":", 1)[0]

        resolve_and_validate_host(host)
        return host

    def _parse_port(self, port: str) -> int:
        if port.lower() in WELL_KNOWN_PORTS:
            return WELL_KNOWN_PORTS[port.lower()]
        try:
            p = int(port)
        except ValueError as e:
            raise SecurityError(f"Invalid port: {port}") from e
        if not (1 <= p <= 65535):
            raise SecurityError("Port must be between 1 and 65535")
        return p

    # ------------------------------------------------------------------
    # DNS
    # ------------------------------------------------------------------

    def dns_lookup(self, target: str) -> Dict[str, Any]:
        """Resolve A/AAAA and reverse lookups for a host."""
        host = self._normalize_host(target)
        result: Dict[str, Any] = {
            "host": host,
            "a": [],
            "aaaa": [],
            "cname_hints": [],
            "reverse": [],
            "errors": [],
        }

        try:
            infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        except socket.gaierror as e:
            result["errors"].append(str(e))
            return result

        seen_v4 = set()
        seen_v6 = set()
        for family, _type, _proto, canon, sockaddr in infos:
            if canon and canon != host and canon not in result["cname_hints"]:
                result["cname_hints"].append(canon)
            addr = sockaddr[0]
            if family == socket.AF_INET:
                if addr not in seen_v4:
                    seen_v4.add(addr)
                    result["a"].append(addr)
            elif family == socket.AF_INET6:
                if addr not in seen_v6:
                    seen_v6.add(addr)
                    result["aaaa"].append(addr)

        for ip in list(result["a"]) + list(result["aaaa"]):
            try:
                name, aliases, _ = socket.gethostbyaddr(ip)
                result["reverse"].append(
                    {"ip": ip, "name": name, "aliases": list(aliases)}
                )
            except (socket.herror, socket.gaierror):
                result["reverse"].append({"ip": ip, "name": None, "aliases": []})

        return result

    def dns_extra(self, target: str) -> Dict[str, Any]:
        """
        Optional MX/NS/TXT via system `dig` if available.
        Falls back gracefully when dig is missing.
        """
        import shutil
        import subprocess

        host = self._normalize_host(target)
        out: Dict[str, Any] = {"host": host, "records": {}, "tool": None}

        dig = shutil.which("dig")
        if not dig:
            out["note"] = "dig not installed; only basic A/AAAA via dns is available"
            return out

        out["tool"] = dig
        for rtype in ("MX", "NS", "TXT", "SOA", "CAA"):
            try:
                proc = subprocess.run(
                    [dig, "+short", host, rtype],
                    capture_output=True,
                    text=True,
                    timeout=8,
                    check=False,
                )
                lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
                out["records"][rtype] = lines
            except (subprocess.TimeoutExpired, OSError) as e:
                out["records"][rtype] = []
                out.setdefault("errors", []).append(f"{rtype}: {e}")

        return out

    # ------------------------------------------------------------------
    # HTTP inspect (DevTools Network-style)
    # ------------------------------------------------------------------

    def http_inspect(
        self,
        url: str,
        *,
        method: str = "GET",
        follow_redirects: bool = True,
        timeout: int = 15,
    ) -> Dict[str, Any]:
        """Inspect an HTTP(S) request like a Network panel entry."""
        url = validate_url(url)
        method = (method or "GET").upper()
        if method not in {"GET", "HEAD", "OPTIONS"}:
            raise SecurityError("Only GET, HEAD, and OPTIONS are allowed")

        t0 = time.perf_counter()
        response = self.session.request(
            method,
            url,
            timeout=timeout,
            allow_redirects=follow_redirects,
            stream=True,
        )
        # Cap body read
        chunks = []
        total = 0
        max_bytes = 512 * 1024
        for chunk in response.iter_content(chunk_size=65536):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                break
            chunks.append(chunk)
        body = b"".join(chunks)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        preview = body[:MAX_HTTP_BODY_PREVIEW]
        try:
            preview_text = preview.decode(response.encoding or "utf-8", errors="replace")
        except Exception:
            preview_text = repr(preview[:200])

        history = []
        for r in response.history:
            history.append(
                {
                    "status": r.status_code,
                    "url": r.url,
                    "location": r.headers.get("Location"),
                }
            )

        return {
            "request": {
                "method": method,
                "url": url,
                "final_url": response.url,
            },
            "timing_ms": elapsed_ms,
            "status": response.status_code,
            "reason": response.reason,
            "http_version": getattr(response.raw, "version", None),
            "headers": dict(response.headers),
            "cookies": {c.name: c.value for c in response.cookies},
            "redirects": history,
            "size_bytes": len(body),
            "content_type": response.headers.get("Content-Type"),
            "body_preview": preview_text,
        }

    # ------------------------------------------------------------------
    # TLS / certificate
    # ------------------------------------------------------------------

    def tls_inspect(self, target: str, port: int = 443) -> Dict[str, Any]:
        """Fetch and summarize the TLS certificate for host:port."""
        host = self._normalize_host(target)
        if not (1 <= port <= 65535):
            raise SecurityError("Port must be between 1 and 65535")

        context = ssl.create_default_context()
        # We still validate hostname/cert; capture peer cert after handshake
        with socket.create_connection((host, port), timeout=MAX_CONNECT_TIMEOUT) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                cipher = ssock.cipher()
                version = ssock.version()

        def _name_dict(entries):
            if not entries:
                return {}
            # entries is a tuple of RDNs
            flat = {}
            for rdn in entries:
                for attr in rdn:
                    if len(attr) >= 2:
                        flat[attr[0]] = attr[1]
            return flat

        not_before = cert.get("notBefore")
        not_after = cert.get("notAfter")
        days_left = None
        if not_after:
            try:
                # OpenSSL format: 'Sep 30 12:00:00 2026 GMT'
                exp = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                exp = exp.replace(tzinfo=timezone.utc)
                days_left = (exp - datetime.now(timezone.utc)).days
            except ValueError:
                days_left = None

        sans = []
        for typ, val in cert.get("subjectAltName", ()) or ():
            sans.append({"type": typ, "value": val})

        return {
            "host": host,
            "port": port,
            "tls_version": version,
            "cipher": {
                "name": cipher[0] if cipher else None,
                "protocol": cipher[1] if cipher else None,
                "bits": cipher[2] if cipher else None,
            },
            "subject": _name_dict(cert.get("subject")),
            "issuer": _name_dict(cert.get("issuer")),
            "serial_number": cert.get("serialNumber"),
            "not_before": not_before,
            "not_after": not_after,
            "days_until_expiry": days_left,
            "subject_alt_names": sans,
        }

    # ------------------------------------------------------------------
    # Connectivity (single port — not a range scan)
    # ------------------------------------------------------------------

    def check_port(self, target: str, port: int) -> Dict[str, Any]:
        """Test TCP connectivity to one host:port (diagnostic only)."""
        host = self._normalize_host(target)
        if not (1 <= int(port) <= 65535):
            raise SecurityError("Port must be between 1 and 65535")
        port = int(port)

        t0 = time.perf_counter()
        status = "closed"
        error = None
        try:
            with socket.create_connection((host, port), timeout=MAX_CONNECT_TIMEOUT):
                status = "open"
        except socket.timeout:
            status = "filtered_or_timeout"
            error = "timeout"
        except OSError as e:
            status = "closed"
            error = str(e)

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "host": host,
            "port": port,
            "status": status,
            "latency_ms": elapsed_ms,
            "error": error,
        }

    def check_services(self, target: str, names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Check a small allowlist of named services (http/https/ssh/...)."""
        host = self._normalize_host(target)
        names = names or ["http", "https"]
        results = []
        for name in names:
            name = name.lower().strip()
            if name not in WELL_KNOWN_PORTS:
                results.append({"service": name, "error": "unknown service name"})
                continue
            port = WELL_KNOWN_PORTS[name]
            check = self.check_port(host, port)
            check["service"] = name
            results.append(check)
        return {"host": host, "checks": results}

    # ------------------------------------------------------------------
    # RDAP / whois-lite (public registration data)
    # ------------------------------------------------------------------

    def rdap_lookup(self, target: str) -> Dict[str, Any]:
        """Query public RDAP for domain registration summary."""
        host = self._normalize_host(target)
        # Strip to registrable-ish domain (simple heuristic: last 2 labels)
        parts = host.split(".")
        domain = ".".join(parts[-2:]) if len(parts) >= 2 else host

        url = f"https://rdap.org/domain/{domain}"
        try:
            validate_url(url)
            resp = self.session.get(url, timeout=12)
            if resp.status_code == 404:
                return {"domain": domain, "found": False}
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            return {"domain": domain, "found": False, "error": str(e)}

        nameservers = []
        for ns in data.get("nameservers") or []:
            if isinstance(ns, dict) and ns.get("ldhName"):
                nameservers.append(ns["ldhName"])

        events = []
        for ev in data.get("events") or []:
            events.append(
                {
                    "action": ev.get("eventAction"),
                    "date": ev.get("eventDate"),
                }
            )

        return {
            "domain": domain,
            "found": True,
            "handle": data.get("handle"),
            "ldh_name": data.get("ldhName"),
            "status": data.get("status"),
            "nameservers": nameservers,
            "events": events,
            "secure_dns": data.get("secureDNS"),
        }

    # ------------------------------------------------------------------
    # Full report
    # ------------------------------------------------------------------

    def full_report(self, target: str) -> Dict[str, Any]:
        """Run DNS + HTTP/TLS + common service checks for a URL or host."""
        host = self._normalize_host(target)
        report: Dict[str, Any] = {
            "target": target,
            "host": host,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dns": self.dns_lookup(host),
            "dns_extra": self.dns_extra(host),
            "services": self.check_services(host, ["http", "https"]),
            "rdap": self.rdap_lookup(host),
        }

        # Prefer HTTPS URL for HTTP/TLS inspect
        if "://" in target.strip():
            url = validate_url(target.strip())
        else:
            url = f"https://{host}/"

        try:
            report["tls"] = self.tls_inspect(host, 443)
        except Exception as e:
            report["tls"] = {"error": str(e)}

        try:
            report["http"] = self.http_inspect(url, method="GET")
        except Exception as e:
            report["http"] = {"error": str(e)}

        return report

    # ------------------------------------------------------------------
    # Pretty printers
    # ------------------------------------------------------------------

    def print_dns(self, data: Dict[str, Any]) -> None:
        print(f"\nDNS LOOKUP — {data.get('host')}")
        print("-" * 60)
        for a in data.get("a") or []:
            print(f"  A     {a}")
        for a in data.get("aaaa") or []:
            print(f"  AAAA  {a}")
        for c in data.get("cname_hints") or []:
            print(f"  HINT  {c}")
        for r in data.get("reverse") or []:
            print(f"  PTR   {r.get('ip')} → {r.get('name') or '(none)'}")
        for err in data.get("errors") or []:
            print(f"  ✗ {err}")

    def print_http(self, data: Dict[str, Any]) -> None:
        if data.get("error"):
            print(f"\n✗ HTTP inspect failed: {data['error']}")
            return
        req = data.get("request") or {}
        print(f"\nHTTP INSPECT — {req.get('method')} {req.get('url')}")
        print("-" * 60)
        print(f"  Status:   {data.get('status')} {data.get('reason')}")
        print(f"  Final:    {req.get('final_url')}")
        print(f"  Time:     {data.get('timing_ms')} ms")
        print(f"  Size:     {data.get('size_bytes')} bytes")
        print(f"  Type:     {data.get('content_type')}")
        if data.get("redirects"):
            print("  Redirects:")
            for r in data["redirects"]:
                print(f"    → {r.get('status')} {r.get('url')}")
        print("  Headers:")
        for k, v in (data.get("headers") or {}).items():
            print(f"    {k}: {v}")

    def print_tls(self, data: Dict[str, Any]) -> None:
        if data.get("error"):
            print(f"\n✗ TLS inspect failed: {data['error']}")
            return
        print(f"\nTLS CERTIFICATE — {data.get('host')}:{data.get('port')}")
        print("-" * 60)
        print(f"  Version:  {data.get('tls_version')}")
        cipher = data.get("cipher") or {}
        print(f"  Cipher:   {cipher.get('name')} ({cipher.get('bits')} bits)")
        subj = data.get("subject") or {}
        iss = data.get("issuer") or {}
        print(f"  Subject:  {subj.get('commonName') or subj}")
        print(f"  Issuer:   {iss.get('commonName') or iss}")
        print(f"  Valid:    {data.get('not_before')} → {data.get('not_after')}")
        days = data.get("days_until_expiry")
        if days is not None:
            flag = "✓" if days > 14 else "⚠"
            print(f"  Expiry:   {flag} {days} days remaining")
        sans = data.get("subject_alt_names") or []
        if sans:
            print("  SANs:")
            for s in sans[:20]:
                print(f"    - {s.get('type')}: {s.get('value')}")

    def print_port(self, data: Dict[str, Any]) -> None:
        print(f"\nPORT CHECK — {data.get('host')}:{data.get('port')}")
        print("-" * 60)
        print(f"  Status:   {data.get('status')}")
        print(f"  Latency:  {data.get('latency_ms')} ms")
        if data.get("error"):
            print(f"  Detail:   {data.get('error')}")

    def print_services(self, data: Dict[str, Any]) -> None:
        print(f"\nSERVICE CHECKS — {data.get('host')}")
        print("-" * 60)
        for c in data.get("checks") or []:
            if c.get("error"):
                print(f"  ✗ {c.get('service')}: {c['error']}")
                continue
            mark = "✓" if c.get("status") == "open" else "✗"
            print(
                f"  {mark} {c.get('service'):8} :{c.get('port'):5}  "
                f"{c.get('status')} ({c.get('latency_ms')} ms)"
            )

    def print_rdap(self, data: Dict[str, Any]) -> None:
        print(f"\nRDAP — {data.get('domain')}")
        print("-" * 60)
        if not data.get("found"):
            print(f"  Not found{': ' + data['error'] if data.get('error') else ''}")
            return
        print(f"  Handle:   {data.get('handle')}")
        print(f"  Status:   {data.get('status')}")
        for ns in data.get("nameservers") or []:
            print(f"  NS:       {ns}")
        for ev in data.get("events") or []:
            print(f"  Event:    {ev.get('action')} @ {ev.get('date')}")


def main():
    """CLI for network toolkit."""
    if len(sys.argv) < 2:
        print(
            """
Usage: python network_toolkit.py <target> [options]

Target: hostname or http(s) URL (public hosts only)

Options:
  --dns                 DNS A/AAAA + reverse lookup
  --dns-extra           MX/NS/TXT via dig (if installed)
  --http                HTTP request inspect (Network-panel style)
  --method <GET|HEAD|OPTIONS>
  --tls                 TLS certificate inspect
  --port <N|name>       Single TCP port check (e.g. 443 or https)
  --services [list]     Named services (default: http,https)
  --rdap                Domain registration (RDAP)
  --full                Full diagnostic report
  --output <file.json>  Save JSON report
  --json                Print JSON to stdout

Examples:
  python network_toolkit.py example.com --dns
  python network_toolkit.py https://example.com --http
  python network_toolkit.py example.com --tls
  python network_toolkit.py example.com --port https
  python network_toolkit.py example.com --full --output net.json
"""
        )
        sys.exit(1)

    target = sys.argv[1]
    args = sys.argv[2:]
    toolkit = NetworkToolkit()

    want_dns = "--dns" in args
    want_dns_extra = "--dns-extra" in args
    want_http = "--http" in args
    want_tls = "--tls" in args
    want_rdap = "--rdap" in args
    want_full = "--full" in args
    want_json = "--json" in args
    want_services = "--services" in args
    output_file = None
    method = "GET"
    port_arg = None

    if "--output" in args:
        idx = args.index("--output") + 1
        if idx < len(args):
            output_file = args[idx]

    if "--method" in args:
        idx = args.index("--method") + 1
        if idx < len(args):
            method = args[idx]

    if "--port" in args:
        idx = args.index("--port") + 1
        if idx < len(args):
            port_arg = args[idx]

    service_names = None
    if want_services:
        idx = args.index("--services") + 1
        if idx < len(args) and not args[idx].startswith("-"):
            service_names = [s.strip() for s in args[idx].split(",") if s.strip()]

    # Default to --full feel when no flags
    if not any(
        [
            want_dns,
            want_dns_extra,
            want_http,
            want_tls,
            want_rdap,
            want_full,
            want_services,
            port_arg is not None,
        ]
    ):
        want_full = True

    report: Dict[str, Any] = {"target": target}

    try:
        if want_full:
            report = toolkit.full_report(target)
            if not want_json:
                toolkit.print_dns(report["dns"])
                if report.get("dns_extra", {}).get("records"):
                    print("\nDNS EXTRA")
                    print("-" * 60)
                    for k, v in report["dns_extra"]["records"].items():
                        for line in v or ["(none)"]:
                            print(f"  {k:4}  {line}")
                toolkit.print_services(report["services"])
                toolkit.print_tls(report.get("tls") or {})
                toolkit.print_http(report.get("http") or {})
                toolkit.print_rdap(report.get("rdap") or {})
        else:
            if want_dns:
                report["dns"] = toolkit.dns_lookup(target)
                if not want_json:
                    toolkit.print_dns(report["dns"])
            if want_dns_extra:
                report["dns_extra"] = toolkit.dns_extra(target)
                if not want_json:
                    print("\nDNS EXTRA")
                    print("-" * 60)
                    for k, v in (report["dns_extra"].get("records") or {}).items():
                        for line in v or ["(none)"]:
                            print(f"  {k:4}  {line}")
                    if report["dns_extra"].get("note"):
                        print(f"  note: {report['dns_extra']['note']}")
            if want_http:
                url = target if "://" in target else f"https://{toolkit._normalize_host(target)}/"
                report["http"] = toolkit.http_inspect(url, method=method)
                if not want_json:
                    toolkit.print_http(report["http"])
            if want_tls:
                report["tls"] = toolkit.tls_inspect(target, 443)
                if not want_json:
                    toolkit.print_tls(report["tls"])
            if port_arg is not None:
                p = toolkit._parse_port(port_arg)
                report["port"] = toolkit.check_port(target, p)
                if not want_json:
                    toolkit.print_port(report["port"])
            if want_services:
                report["services"] = toolkit.check_services(target, service_names)
                if not want_json:
                    toolkit.print_services(report["services"])
            if want_rdap:
                report["rdap"] = toolkit.rdap_lookup(target)
                if not want_json:
                    toolkit.print_rdap(report["rdap"])

        if want_json:
            print(json.dumps(report, indent=2, default=str))

        if output_file:
            path = safe_write_json(output_file, report)
            print(f"\n✓ Report saved to {path}")

    except SecurityError as e:
        print(f"✗ Security: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
