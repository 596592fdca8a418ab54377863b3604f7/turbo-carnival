#!/usr/bin/env python3
"""
Web Scraper - Fast web scraping using requests and BeautifulSoup
"""

import sys
import json
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

# Allow running as script or via cli package path
try:
    from utils.security import (
        SecurityError,
        create_safe_session,
        safe_get,
        safe_write_json,
        validate_url,
    )
except ImportError:
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from utils.security import (
        SecurityError,
        create_safe_session,
        safe_get,
        safe_write_json,
        validate_url,
    )


class WebScraper:
    """Fast web scraper using requests and BeautifulSoup"""

    def __init__(self):
        self.session = None
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

    def fetch(self, url: str, timeout: int = 10) -> Optional[str]:
        """Fetch webpage content with SSRF and size guards"""
        try:
            validate_url(url)
            response, content = safe_get(self.session, url, timeout=timeout)
            # Prefer charset from response; fall back to utf-8
            text = content.decode(response.encoding or "utf-8", errors="replace")
            print(f"✓ Fetched {url} (Status: {response.status_code})")
            return text
        except SecurityError as e:
            print(f"✗ Security: blocked request to {url}: {e}")
            return None
        except self.requests.exceptions.RequestException as e:
            print(f"✗ Error fetching {url}: {e}")
            return None

    def parse(self, html: str):
        """Parse HTML content"""
        return self.BeautifulSoup(html, "html.parser")

    def extract_title(self, soup) -> str:
        """Extract page title"""
        title = soup.find("title")
        return title.get_text().strip() if title else "No title"

    def extract_meta(self, soup) -> Dict:
        """Extract meta tags"""
        meta_data = {}
        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property")
            content = meta.get("content")
            if name and content:
                meta_data[name] = content
        return meta_data

    def extract_links(self, soup, base_url: str) -> List[Dict]:
        """Extract all links from page"""
        links = []
        base_netloc = urlparse(base_url).netloc
        for link in soup.find_all("a", href=True):
            href = link["href"]
            # Skip dangerous / non-http schemes early
            if href.startswith(("javascript:", "data:", "vbscript:", "file:")):
                continue
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            if parsed.scheme not in ("http", "https", ""):
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

    def extract_images(self, soup, base_url: str) -> List[Dict]:
        """Extract all images from page"""
        images = []
        for img in soup.find_all("img", src=True):
            src = img["src"]
            if src.startswith(("javascript:", "data:", "vbscript:", "file:")):
                continue
            full_url = urljoin(base_url, src)
            alt = img.get("alt", "")
            images.append({"url": full_url, "alt": alt})
        return images

    def extract_text(self, soup, clean: bool = True) -> str:
        """Extract text content from page"""
        if clean:
            for script in soup(["script", "style"]):
                script.decompose()
        return soup.get_text(separator="\n", strip=True)

    def extract_headings(self, soup) -> Dict[str, List[str]]:
        """Extract all headings (h1-h6)"""
        headings = {f"h{i}": [] for i in range(1, 7)}
        for i in range(1, 7):
            for heading in soup.find_all(f"h{i}"):
                headings[f"h{i}"].append(heading.get_text().strip())
        return headings

    def extract_forms(self, soup) -> List[Dict]:
        """Extract all forms from page"""
        forms = []
        for form in soup.find_all("form"):
            form_data = {
                "action": form.get("action", ""),
                "method": form.get("method", "GET").upper(),
                "inputs": [],
            }
            for input_field in form.find_all(["input", "textarea", "select"]):
                field_data = {
                    "type": input_field.get("type", "text"),
                    "name": input_field.get("name", ""),
                    "id": input_field.get("id", ""),
                }
                if field_data["name"] or field_data["id"]:
                    form_data["inputs"].append(field_data)
            forms.append(form_data)
        return forms

    def scrape_page(self, url: str, extract: List[str] = None) -> Dict:
        """Scrape a single page with multiple extractions"""
        if extract is None:
            extract = ["title", "meta", "links", "text", "headings"]

        html = self.fetch(url)
        if not html:
            return {}

        soup = self.parse(html)
        result = {"url": url}

        if "title" in extract:
            result["title"] = self.extract_title(soup)

        if "meta" in extract:
            result["meta"] = self.extract_meta(soup)

        if "links" in extract:
            result["links"] = self.extract_links(soup, url)

        if "images" in extract:
            result["images"] = self.extract_images(soup, url)

        if "text" in extract:
            result["text"] = self.extract_text(soup)

        if "headings" in extract:
            result["headings"] = self.extract_headings(soup)

        if "forms" in extract:
            result["forms"] = self.extract_forms(soup)

        return result

    def scrape_multiple(self, urls: List[str], extract: List[str] = None) -> List[Dict]:
        """Scrape multiple pages"""
        results = []
        for url in urls:
            result = self.scrape_page(url, extract)
            if result:
                results.append(result)
        return results

    def save_to_json(self, data: Dict, filename: str):
        """Save scraped data to JSON file (path-traversal safe)"""
        try:
            path = safe_write_json(filename, data)
            print(f"✓ Saved data to {path}")
        except SecurityError as e:
            print(f"✗ Security: refused to write file: {e}")

    def print_summary(self, data: Dict):
        """Print summary of scraped data"""
        print("\n" + "=" * 60)
        print("WEB SCRAPE SUMMARY")
        print("=" * 60)
        print(f"URL:        {data.get('url', 'N/A')}")
        print(f"Title:      {data.get('title', 'N/A')}")

        if "meta" in data:
            print(f"Meta tags:  {len(data['meta'])}")

        if "links" in data:
            internal = sum(1 for link in data["links"] if link["internal"])
            external = len(data["links"]) - internal
            print(
                f"Links:      {len(data['links'])} "
                f"(Internal: {internal}, External: {external})"
            )

        if "images" in data:
            print(f"Images:     {len(data['images'])}")

        if "forms" in data:
            print(f"Forms:      {len(data['forms'])}")

        if "text" in data:
            print(f"Text length: {len(data['text'])} characters")

        print("=" * 60)


def main():
    """Main entry point for web scraper"""
    if len(sys.argv) < 2:
        print("Usage: python web_scraper.py <url> [options]")
        print("\nOptions:")
        print(
            "  --extract <items>    Comma-separated list: "
            "title,meta,links,images,text,headings,forms"
        )
        print("  --output <file>      Save output to JSON file")
        print("  --summary            Show summary only")
        print("  --links              Show all links")
        print("  --headings           Show all headings")
        sys.exit(1)

    url = sys.argv[1]
    scraper = WebScraper()

    extract = ["title", "meta", "links", "text", "headings"]
    output_file = None
    show_summary = False
    show_links = False
    show_headings = False

    if "--extract" in sys.argv:
        extract_idx = sys.argv.index("--extract") + 1
        if extract_idx < len(sys.argv):
            extract = [x.strip() for x in sys.argv[extract_idx].split(",") if x.strip()]

    if "--output" in sys.argv:
        output_idx = sys.argv.index("--output") + 1
        if output_idx < len(sys.argv):
            output_file = sys.argv[output_idx]

    if "--summary" in sys.argv:
        show_summary = True

    if "--links" in sys.argv:
        show_links = True

    if "--headings" in sys.argv:
        show_headings = True

    data = scraper.scrape_page(url, extract)

    if not data:
        sys.exit(1)

    if show_summary:
        scraper.print_summary(data)

    if show_links and "links" in data:
        print(f"\nLinks ({len(data['links'])} found):")
        print("-" * 80)
        for link in data["links"][:20]:
            marker = "[INT]" if link["internal"] else "[EXT]"
            print(f"{marker} {link['text'][:50]:<50} {link['url']}")
        if len(data["links"]) > 20:
            print(f"... and {len(data['links']) - 20} more links")

    if show_headings and "headings" in data:
        print("\nHeadings:")
        print("-" * 80)
        for level, headings in data["headings"].items():
            if headings:
                print(f"\n{level.upper()}:")
                for heading in headings:
                    print(f"  {heading}")

    if output_file:
        scraper.save_to_json(data, output_file)

    if not show_summary and not show_links and not show_headings:
        print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
