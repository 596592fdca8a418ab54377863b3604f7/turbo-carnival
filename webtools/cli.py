#!/usr/bin/env python3
"""
WebTools CLI - Unified terminal toolkit (Web + Network + DevTools bridge)

Organized like a compact ops toolkit: scrape/analyze the web, inspect network
traffic and DNS/TLS, and call sibling DevTools commands from one entry point.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Add current directory to path for imports
_WEBTOOLS_ROOT = Path(__file__).resolve().parent
if str(_WEBTOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(_WEBTOOLS_ROOT))

_REPO_ROOT = _WEBTOOLS_ROOT.parent
_DEVTOOLS_ROOT = _REPO_ROOT / "devtools"
_DEVTOOLS_CLI = _DEVTOOLS_ROOT / "cli.py"

__version__ = "1.1.0"


def print_banner():
    """Print CLI banner"""
    print(
        f"""
╔═══════════════════════════════════════════════════════════════╗
║              WebTools CLI v{__version__:<8}                         ║
║     Web · Network · DevTools  — terminal ops toolkit          ║
╚═══════════════════════════════════════════════════════════════╝
""",
        flush=True,
    )


def print_help():
    """Print help information"""
    print(
        """
WebTools CLI — unified toolkit (web automation + network + devtools)

Usage: python cli.py <command> [arguments]
       python cli.py menu              Interactive command menu

─── WEB ────────────────────────────────────────────────────────
  scrape              Fast web scraping (requests + BeautifulSoup)
  content             Extract scripts, styles, emails, tables, …
  links               Analyze / crawl links, broken-link checks
  insights            SEO, performance, security, accessibility
  forms               Form listing / submit / login helpers
  browser             Playwright browser automation
  workflow            Multi-step JSON workflow runner

─── NETWORK (diagnostics) ──────────────────────────────────────
  network <target>    Full network report (DNS + HTTP + TLS + RDAP)
  dns <host>          DNS A/AAAA + reverse lookup
  http <url>          HTTP inspect (DevTools Network-style)
  tls <host>          TLS certificate inspect
  port <host> <port>  Single TCP connectivity check
  services <host>     Named service checks (http, https, ssh, …)
  rdap <domain>       Domain registration via RDAP

─── DEVTOOLS (sibling package) ─────────────────────────────────
  devtools …          Proxy to ../devtools/cli.py
  logs <file>         Alias → devtools log-analyzer
  metrics <path>      Alias → devtools code-metrics
  transform …         Alias → devtools data-transform
  files <dir>         Alias → devtools file-organizer

─── META ───────────────────────────────────────────────────────
  menu                Interactive menu
  help                Show this help
  version             Show version

Network examples:
  python cli.py network example.com
  python cli.py dns example.com --dns-extra
  python cli.py http https://example.com --method HEAD
  python cli.py tls example.com
  python cli.py port example.com 443
  python cli.py services example.com --services http,https,ssh

DevTools examples:
  python cli.py logs ../devtools/sample.log
  python cli.py metrics ../webtools --details
  python cli.py transform data.json out.csv --json-to-csv
  python cli.py files . --ext .py

Web examples:
  python cli.py scrape https://example.com --summary
  python cli.py insights https://example.com --score
  python cli.py browser https://example.com --screenshot page.png
"""
    )


def _dispatch(module_argv_name: str, args, runner):
    """Run a subcommand without permanently corrupting process argv."""
    original = sys.argv[:]
    try:
        sys.argv = [module_argv_name] + list(args)
        runner()
    finally:
        sys.argv = original


def _safe_cmd(command: str) -> str:
    return "".join(ch for ch in command if ch.isprintable())[:64]


def run_devtools(args) -> int:
    """Proxy remaining args to the sibling DevTools CLI."""
    if not _DEVTOOLS_CLI.is_file():
        print(f"✗ DevTools not found at {_DEVTOOLS_CLI}")
        print("  Expected sibling package: ../devtools/")
        return 1

    cmd = [sys.executable, str(_DEVTOOLS_CLI)] + list(args)
    print(f"→ DevTools: {' '.join(args) if args else '(help)'}", flush=True)
    try:
        completed = subprocess.run(cmd, check=False)
        return int(completed.returncode or 0)
    except OSError as e:
        print(f"✗ Failed to launch DevTools: {e}")
        return 1


def run_network(args) -> None:
    """Run network toolkit with given args (target first)."""
    from network.network_toolkit import main as network_main

    _dispatch("network_toolkit.py", args, network_main)


def interactive_menu():
    """Simple interactive launcher."""
    options = [
        ("1", "Scrape a page", "scrape"),
        ("2", "Content extract", "content"),
        ("3", "Link analyze", "links"),
        ("4", "Web insights", "insights"),
        ("5", "Network full report", "network"),
        ("6", "DNS lookup", "dns"),
        ("7", "HTTP inspect", "http"),
        ("8", "TLS certificate", "tls"),
        ("9", "Port check", "port"),
        ("10", "DevTools: log analyzer", "logs"),
        ("11", "DevTools: code metrics", "metrics"),
        ("12", "DevTools: file organizer", "files"),
        ("h", "Help", "help"),
        ("q", "Quit", None),
    ]

    print("Select a tool:\n")
    for key, label, _ in options:
        print(f"  [{key:>2}]  {label}")

    choice = input("\nChoice: ").strip().lower()
    mapping = {k: cmd for k, _, cmd in options}
    if choice not in mapping:
        print("Invalid choice.")
        return

    cmd = mapping[choice]
    if cmd is None:
        return
    if cmd == "help":
        print_help()
        return

    # Prompt for remaining args
    if cmd == "port":
        host = input("Host: ").strip()
        port = input("Port (number or name like https): ").strip()
        sys.argv = ["cli.py", cmd, host, port]
    elif cmd in ("logs", "metrics", "files"):
        path = input("Path: ").strip()
        extra = input("Extra flags (optional): ").strip()
        extra_args = extra.split() if extra else []
        sys.argv = ["cli.py", cmd, path] + extra_args
    else:
        target = input("Target (URL or host): ").strip()
        extra = input("Extra flags (optional): ").strip()
        extra_args = extra.split() if extra else []
        sys.argv = ["cli.py", cmd, target] + extra_args

    main()


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print_banner()
        print_help()
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    if command in ("help", "--help", "-h"):
        print_banner()
        print_help()
        return

    if command in ("version", "--version", "-V"):
        print(f"WebTools CLI {__version__}")
        return

    if command == "menu":
        print_banner()
        interactive_menu()
        return

    print_banner()

    # ── Web commands ──────────────────────────────────────────────
    if command == "scrape":
        if not args:
            print("Error: Please specify a URL")
            sys.exit(1)
        from scrapers.web_scraper import main as scrape_main

        _dispatch("web_scraper.py", args, scrape_main)

    elif command == "content":
        if not args:
            print("Error: Please specify a URL")
            sys.exit(1)
        from scrapers.content_extractor import main as content_main

        _dispatch("content_extractor.py", args, content_main)

    elif command == "links":
        if not args:
            print("Error: Please specify a URL")
            sys.exit(1)
        from analyzers.link_analyzer import main as links_main

        _dispatch("link_analyzer.py", args, links_main)

    elif command == "insights":
        if not args:
            print("Error: Please specify a URL")
            sys.exit(1)
        from analyzers.web_insights import main as insights_main

        _dispatch("web_insights.py", args, insights_main)

    elif command == "forms":
        if not args:
            print("Error: Please specify a URL")
            sys.exit(1)
        from automation.form_automation import main as forms_main

        _dispatch("form_automation.py", args, forms_main)

    elif command == "browser":
        if not args:
            print("Error: Please specify a URL")
            sys.exit(1)
        from automation.browser_automation import main as browser_main

        _dispatch("browser_automation.py", args, browser_main)

    elif command == "workflow":
        if not args:
            print("Error: Please specify a workflow file")
            sys.exit(1)
        from automation.workflow_automation import main as workflow_main

        _dispatch("workflow_automation.py", args, workflow_main)

    # ── Network commands ──────────────────────────────────────────
    elif command == "network":
        if not args:
            print("Error: Please specify a host or URL")
            sys.exit(1)
        # Default to full report
        if not any(
            a.startswith("--")
            for a in args[1:]
        ) and len(args) == 1:
            run_network([args[0], "--full"])
        else:
            # If user didn't pass a mode flag, add --full
            flags = {a for a in args if a.startswith("--")}
            mode_flags = {
                "--dns",
                "--dns-extra",
                "--http",
                "--tls",
                "--port",
                "--services",
                "--rdap",
                "--full",
            }
            if not (flags & mode_flags):
                run_network([args[0], "--full"] + args[1:])
            else:
                run_network(args)

    elif command == "dns":
        if not args:
            print("Error: Please specify a host")
            sys.exit(1)
        net_args = [args[0], "--dns"]
        if "--dns-extra" in args:
            net_args.append("--dns-extra")
        if "--json" in args:
            net_args.append("--json")
        if "--output" in args:
            idx = args.index("--output")
            net_args.append("--output")
            if idx + 1 < len(args):
                net_args.append(args[idx + 1])
        run_network(net_args)

    elif command == "http":
        if not args:
            print("Error: Please specify a URL")
            sys.exit(1)
        net_args = [args[0], "--http"]
        i = 1
        while i < len(args):
            if args[i] == "--method" and i + 1 < len(args):
                net_args.extend(["--method", args[i + 1]])
                i += 2
                continue
            if args[i] == "--json":
                net_args.append("--json")
            if args[i] == "--output" and i + 1 < len(args):
                net_args.extend(["--output", args[i + 1]])
                i += 2
                continue
            i += 1
        run_network(net_args)

    elif command == "tls":
        if not args:
            print("Error: Please specify a host")
            sys.exit(1)
        net_args = [args[0], "--tls"]
        if "--json" in args:
            net_args.append("--json")
        if "--output" in args:
            idx = args.index("--output")
            net_args.append("--output")
            if idx + 1 < len(args):
                net_args.append(args[idx + 1])
        run_network(net_args)

    elif command == "port":
        if len(args) < 2:
            print("Error: Usage: port <host> <port|name>")
            sys.exit(1)
        net_args = [args[0], "--port", args[1]]
        if "--json" in args:
            net_args.append("--json")
        run_network(net_args)

    elif command == "services":
        if not args:
            print("Error: Please specify a host")
            sys.exit(1)
        net_args = [args[0], "--services"]
        if "--services" in args:
            idx = args.index("--services")
            if idx + 1 < len(args):
                net_args.append(args[idx + 1])
        elif len(args) > 1 and not args[1].startswith("-"):
            net_args.append(args[1])
        if "--json" in args:
            net_args.append("--json")
        run_network(net_args)

    elif command == "rdap":
        if not args:
            print("Error: Please specify a domain")
            sys.exit(1)
        net_args = [args[0], "--rdap"]
        if "--json" in args:
            net_args.append("--json")
        run_network(net_args)

    # ── DevTools bridge ───────────────────────────────────────────
    elif command == "devtools":
        sys.exit(run_devtools(args))

    elif command == "logs":
        sys.exit(run_devtools(["log-analyzer"] + args))

    elif command == "metrics":
        sys.exit(run_devtools(["code-metrics"] + args))

    elif command == "transform":
        sys.exit(run_devtools(["data-transform"] + args))

    elif command == "files":
        sys.exit(run_devtools(["file-organizer"] + args))

    else:
        print(f"Error: Unknown command '{_safe_cmd(command)}'")
        print("Run: python cli.py help")
        sys.exit(1)


if __name__ == "__main__":
    main()
