#!/usr/bin/env python3
"""
Link Analyzer - Extract and analyze links from web pages
"""

import sys
from typing import Dict, List
from urllib.parse import urlparse, urljoin
from collections import Counter

try:
    from utils.security import (
        SecurityError,
        create_safe_session,
        safe_get,
        safe_write_json,
        safe_write_text,
        validate_url,
        DEFAULT_MAX_CRAWL_PAGES,
        DEFAULT_MAX_CRAWL_DEPTH,
        DEFAULT_MAX_BROKEN_LINK_CHECKS,
    )
except ImportError:
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from utils.security import (
        SecurityError,
        create_safe_session,
        safe_get,
        safe_write_json,
        safe_write_text,
        validate_url,
        DEFAULT_MAX_CRAWL_PAGES,
        DEFAULT_MAX_CRAWL_DEPTH,
        DEFAULT_MAX_BROKEN_LINK_CHECKS,
    )


class LinkAnalyzer:
    """Analyze links and link structures"""

    def __init__(self):
        try:
            import requests
            from bs4 import BeautifulSoup
            self.requests = requests
            self.BeautifulSoup = BeautifulSoup
            self.session = create_safe_session(requests)
        except ImportError as e:
            print(f"✗ Error: Required library not installed: {e}")
            print("Install with: pip install requests beautifulsoup4")
            sys.exit(1)

    def fetch(self, url: str) -> str:
        """Fetch webpage content with SSRF and size guards"""
        try:
            validate_url(url)
            response, content = safe_get(self.session, url, timeout=10)
            return content.decode(response.encoding or "utf-8", errors="replace")
        except SecurityError as e:
            print(f"✗ Security: blocked request to {url}: {e}")
            return ""
        except self.requests.exceptions.RequestException as e:
            print(f"✗ Error fetching {url}: {e}")
            return ""

    def extract_links(self, html: str, base_url: str) -> List[Dict]:
        """Extract all links from HTML"""
        soup = self.BeautifulSoup(html, "html.parser")
        links = []
        base_netloc = urlparse(base_url).netloc

        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.startswith(("javascript:", "data:", "vbscript:", "file:", "mailto:", "tel:")):
                continue
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            if parsed.scheme not in ("http", "https"):
                continue
            text = link.get_text().strip()
            links.append(
                {
                    "url": full_url,
                    "text": text,
                    "internal": parsed.netloc == base_netloc,
                }
            )

        return links

    def analyze_links(self, links: List[Dict]) -> Dict:
        """Analyze link structure"""
        if not links:
            return {
                "total_links": 0,
                "internal_links": 0,
                "external_links": 0,
                "domains": Counter(),
                "link_texts": Counter(),
                "broken_links": [],
                "unique_domains": 0,
            }

        analysis = {
            "total_links": len(links),
            "internal_links": 0,
            "external_links": 0,
            "domains": Counter(),
            "link_texts": Counter(),
            "broken_links": [],
            "unique_domains": set(),
        }

        for link in links:
            if link["internal"]:
                analysis["internal_links"] += 1
            else:
                analysis["external_links"] += 1
                domain = urlparse(link["url"]).netloc
                analysis["domains"][domain] += 1
                analysis["unique_domains"].add(domain)

            if link["text"]:
                analysis["link_texts"][link["text"]] += 1

        analysis["unique_domains"] = len(analysis["unique_domains"])
        return analysis

    def crawl_links(
        self,
        start_url: str,
        max_depth: int = 1,
        max_pages: int = 10,
    ) -> Dict:
        """Crawl links from a starting URL (same-origin only, capped)."""
        # Enforce hard ceilings
        max_depth = max(0, min(int(max_depth), DEFAULT_MAX_CRAWL_DEPTH))
        max_pages = max(1, min(int(max_pages), DEFAULT_MAX_CRAWL_PAGES))

        start_netloc = urlparse(start_url).netloc
        visited = set()
        to_visit = [(start_url, 0)]
        all_links = []

        while to_visit and len(visited) < max_pages:
            current_url, depth = to_visit.pop(0)

            if current_url in visited or depth > max_depth:
                continue

            # Stay on the original start domain (fix unused base_domain bug)
            if urlparse(current_url).netloc != start_netloc:
                continue

            visited.add(current_url)
            print(f"Crawling: {current_url} (Depth: {depth})")

            html = self.fetch(current_url)
            if not html:
                continue

            # Mark internal relative to start domain, not the current page alone
            links = self.extract_links(html, current_url)
            for link in links:
                link["internal"] = urlparse(link["url"]).netloc == start_netloc
            all_links.extend(links)

            if depth < max_depth:
                for link in links:
                    target = link["url"]
                    if (
                        link["internal"]
                        and target not in visited
                        and urlparse(target).netloc == start_netloc
                    ):
                        to_visit.append((target, depth + 1))

        analysis = self.analyze_links(all_links)
        analysis["visited_pages"] = len(visited)
        analysis["all_links"] = all_links
        return analysis

    def find_broken_links(self, links: List[Dict]) -> List[Dict]:
        """Check for broken links (404 errors), with rate/count caps."""
        broken = []
        # Deduplicate and cap checks
        seen = set()
        checked = 0
        for link in links:
            url = link["url"]
            if url in seen:
                continue
            seen.add(url)
            if checked >= DEFAULT_MAX_BROKEN_LINK_CHECKS:
                print(
                    f"  (Stopped after {DEFAULT_MAX_BROKEN_LINK_CHECKS} "
                    "link checks — limit reached)"
                )
                break
            checked += 1
            try:
                validate_url(url)
                response = self.session.head(
                    url, timeout=5, allow_redirects=True
                )
                if response.status_code >= 400:
                    broken.append(
                        {
                            "url": url,
                            "status": response.status_code,
                            "text": link["text"],
                        }
                    )
            except SecurityError:
                # Treat blocked targets as non-checkable, not broken
                continue
            except self.requests.exceptions.RequestException:
                broken.append(
                    {"url": url, "status": "ERROR", "text": link["text"]}
                )
        return broken

    def print_analysis(self, analysis: Dict):
        """Print link analysis summary"""
        print("\n" + "=" * 60)
        print("LINK ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"Total Links:        {analysis.get('total_links', 0)}")
        print(f"Internal Links:     {analysis.get('internal_links', 0)}")
        print(f"External Links:     {analysis.get('external_links', 0)}")
        print(f"Unique Domains:     {analysis.get('unique_domains', 0)}")
        print(f"Pages Crawled:      {analysis.get('visited_pages', 1)}")
        print("=" * 60)

        domains = analysis.get("domains")
        if domains:
            print("\nTop External Domains:")
            print("-" * 60)
            for domain, count in domains.most_common(10):
                print(f"  {domain}: {count} links")

        link_texts = analysis.get("link_texts")
        if link_texts:
            print("\nTop Link Texts:")
            print("-" * 60)
            for text, count in link_texts.most_common(10):
                print(f"  '{text}': {count} links")

    def export_links(self, links: List[Dict], filename: str):
        """Export links to file (path-traversal safe)"""
        try:
            path = safe_write_json(filename, links)
            print(f"✓ Exported {len(links)} links to {path}")
        except SecurityError as e:
            print(f"✗ Security: refused to write file: {e}")

    def export_sitemap(self, links: List[Dict], filename: str):
        """Export links as sitemap (path-traversal safe)"""
        unique_urls = sorted(set(link["url"] for link in links))
        try:
            path = safe_write_text(filename, "\n".join(unique_urls) + "\n")
            print(f"✓ Exported {len(unique_urls)} unique URLs to {path}")
        except SecurityError as e:
            print(f"✗ Security: refused to write file: {e}")


def main():
    """Main entry point for link analyzer"""
    if len(sys.argv) < 2:
        print("Usage: python link_analyzer.py <url> [options]")
        print("\nOptions:")
        print("  --crawl <depth>       Crawl links (default depth: 1)")
        print("  --max-pages <N>       Maximum pages to crawl (default: 10)")
        print("  --check-broken        Check for broken links")
        print("  --export <file>       Export links to JSON")
        print("  --sitemap <file>      Export as sitemap")
        sys.exit(1)

    url = sys.argv[1]
    analyzer = LinkAnalyzer()

    crawl_depth = 1
    max_pages = 10
    check_broken = False
    export_file = None
    sitemap_file = None
    do_crawl = False

    if "--crawl" in sys.argv:
        do_crawl = True
        depth_idx = sys.argv.index("--crawl") + 1
        if depth_idx < len(sys.argv) and not sys.argv[depth_idx].startswith("--"):
            try:
                crawl_depth = int(sys.argv[depth_idx])
            except ValueError:
                print("✗ Error: --crawl depth must be an integer")
                sys.exit(1)

    if "--max-pages" in sys.argv:
        pages_idx = sys.argv.index("--max-pages") + 1
        if pages_idx < len(sys.argv):
            try:
                max_pages = int(sys.argv[pages_idx])
            except ValueError:
                print("✗ Error: --max-pages must be an integer")
                sys.exit(1)

    if "--check-broken" in sys.argv:
        check_broken = True

    if "--export" in sys.argv:
        export_idx = sys.argv.index("--export") + 1
        if export_idx < len(sys.argv):
            export_file = sys.argv[export_idx]

    if "--sitemap" in sys.argv:
        sitemap_idx = sys.argv.index("--sitemap") + 1
        if sitemap_idx < len(sys.argv):
            sitemap_file = sys.argv[sitemap_idx]

    # Fixed: --crawl 1 previously skipped crawl_links entirely
    if do_crawl:
        print(f"Crawling {url} (Depth: {crawl_depth}, Max pages: {max_pages})")
        analysis = analyzer.crawl_links(url, crawl_depth, max_pages)
        links = analysis["all_links"]
    else:
        html = analyzer.fetch(url)
        if not html:
            sys.exit(1)
        links = analyzer.extract_links(html, url)
        analysis = analyzer.analyze_links(links)

    analyzer.print_analysis(analysis)

    if check_broken:
        print("\nChecking for broken links...")
        broken = analyzer.find_broken_links(links)
        if broken:
            print(f"\nFound {len(broken)} broken links:")
            for link in broken[:10]:
                print(f"  {link['status']}: {link['url']}")
        else:
            print("✓ No broken links found")

    if export_file:
        analyzer.export_links(links, export_file)

    if sitemap_file:
        analyzer.export_sitemap(links, sitemap_file)


if __name__ == "__main__":
    main()
