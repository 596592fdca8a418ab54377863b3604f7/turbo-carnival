#!/usr/bin/env python3
"""
Content Extractor - Extract code, scripts, and specific content from web pages
"""

import sys
import re
import json
from typing import Dict, List
from urllib.parse import urljoin

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


# Safer patterns (avoid overly greedy / ReDoS-prone expressions)
_EMAIL_RE = re.compile(
    r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}(?![A-Za-z0-9._%+-])"
)
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)"
)
_URL_RE = re.compile(r"https?://[^\s<>\"{}|\\^`\[\]]{1,2048}")
_PRICE_RE = re.compile(r"[$€£¥]\s?\d{1,10}(?:[.,]\d{2})?|\d{1,10}[.,]\d{2}\s?[$€£¥]")
_DATE_RES = [
    re.compile(r"\d{4}-\d{2}-\d{2}"),
    re.compile(r"\d{2}/\d{2}/\d{4}"),
    re.compile(
        r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}",
        re.IGNORECASE,
    ),
]


class ContentExtractor:
    """Extract specific content from web pages"""

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

    def extract_scripts(self, html: str, base_url: str) -> List[Dict]:
        """Extract all JavaScript from page"""
        soup = self.BeautifulSoup(html, "html.parser")
        scripts = []

        for script in soup.find_all("script"):
            script_data = {
                "type": script.get("type", "text/javascript"),
                "src": script.get("src", ""),
                "content": "",
                "inline": False,
            }

            if script.get("src"):
                script_data["src"] = urljoin(base_url, script["src"])
                script_data["inline"] = False
            else:
                # Cap inline script size to avoid huge dumps / memory issues
                raw = script.string or ""
                script_data["content"] = raw[:100_000]
                script_data["inline"] = True

            scripts.append(script_data)

        return scripts

    def extract_styles(self, html: str, base_url: str) -> List[Dict]:
        """Extract all CSS from page"""
        soup = self.BeautifulSoup(html, "html.parser")
        styles = []

        for style in soup.find_all("style"):
            raw = style.string or ""
            styles.append(
                {
                    "type": style.get("type", "text/css"),
                    "content": raw[:100_000],
                    "inline": True,
                }
            )

        for link in soup.find_all("link", rel="stylesheet"):
            styles.append(
                {
                    "type": "text/css",
                    "href": urljoin(base_url, link.get("href", "")),
                    "inline": False,
                }
            )

        return styles

    def extract_code_blocks(self, html: str) -> List[Dict]:
        """Extract code blocks (pre, code tags)"""
        soup = self.BeautifulSoup(html, "html.parser")
        code_blocks = []

        for pre in soup.find_all("pre"):
            code = pre.find("code")
            content = code.get_text() if code else pre.get_text()
            classes = code.get("class", [""]) if code else [""]
            lang = classes[0] if classes else ""
            code_blocks.append(
                {
                    "language": lang if isinstance(lang, str) else "",
                    "content": content.strip()[:100_000],
                    "tag": "pre",
                }
            )

        for code in soup.find_all("code"):
            if not code.find_parent("pre"):
                classes = code.get("class", [""])
                lang = classes[0] if classes else ""
                code_blocks.append(
                    {
                        "language": lang if isinstance(lang, str) else "",
                        "content": code.get_text().strip()[:100_000],
                        "tag": "code",
                    }
                )

        return code_blocks

    def extract_tables(self, html: str) -> List[Dict]:
        """Extract all tables from page"""
        soup = self.BeautifulSoup(html, "html.parser")
        tables = []

        for idx, table in enumerate(soup.find_all("table")):
            table_data = {"index": idx, "headers": [], "rows": []}

            header_row = table.find("tr")
            if header_row:
                for th in header_row.find_all(["th", "td"]):
                    table_data["headers"].append(th.get_text().strip())

            for row in table.find_all("tr")[1:]:
                row_data = []
                for cell in row.find_all(["td", "th"]):
                    row_data.append(cell.get_text().strip())
                if row_data:
                    table_data["rows"].append(row_data)
                # Cap rows per table
                if len(table_data["rows"]) >= 1000:
                    break

            tables.append(table_data)
            if len(tables) >= 100:
                break

        return tables

    def extract_emails(self, text: str) -> List[str]:
        """Extract email addresses from text"""
        # Bound scan length against ReDoS / huge pages
        sample = text[:500_000]
        return list(set(_EMAIL_RE.findall(sample)))

    def extract_phone_numbers(self, text: str) -> List[str]:
        """Extract phone numbers from text (US-style; avoids catastrophic regex)"""
        sample = text[:500_000]
        return list(set(_PHONE_RE.findall(sample)))

    def extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text"""
        sample = text[:500_000]
        return list(set(_URL_RE.findall(sample)))

    def extract_prices(self, text: str) -> List[str]:
        """Extract prices from text"""
        sample = text[:500_000]
        return list(set(_PRICE_RE.findall(sample)))

    def extract_dates(self, text: str) -> List[str]:
        """Extract dates from text"""
        sample = text[:500_000]
        dates = []
        for pattern in _DATE_RES:
            dates.extend(pattern.findall(sample))
        return list(set(dates))

    def extract_meta_tags(self, html: str) -> Dict:
        """Extract all meta tags"""
        soup = self.BeautifulSoup(html, "html.parser")
        meta_data = {}

        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property") or meta.get("http-equiv")
            content = meta.get("content")
            if name and content:
                meta_data[name] = content

        return meta_data

    def extract_json_ld(self, html: str) -> List[Dict]:
        """Extract JSON-LD structured data"""
        soup = self.BeautifulSoup(html, "html.parser")
        json_ld_data = []

        for script in soup.find_all("script", type="application/ld+json"):
            raw = script.string
            if not raw:
                continue
            try:
                data = json.loads(raw)
                json_ld_data.append(data)
            except (json.JSONDecodeError, TypeError, ValueError):
                continue

        return json_ld_data

    def extract_all(self, url: str) -> Dict:
        """Extract all content types from page"""
        html = self.fetch(url)
        if not html:
            return {}

        soup = self.BeautifulSoup(html, "html.parser")
        text = soup.get_text()

        return {
            "url": url,
            "scripts": self.extract_scripts(html, url),
            "styles": self.extract_styles(html, url),
            "code_blocks": self.extract_code_blocks(html),
            "tables": self.extract_tables(html),
            "emails": self.extract_emails(text),
            "phone_numbers": self.extract_phone_numbers(text),
            "urls": self.extract_urls(text),
            "prices": self.extract_prices(text),
            "dates": self.extract_dates(text),
            "meta_tags": self.extract_meta_tags(html),
            "json_ld": self.extract_json_ld(html),
        }

    def print_summary(self, data: Dict):
        """Print extraction summary"""
        print("\n" + "=" * 60)
        print("CONTENT EXTRACTION SUMMARY")
        print("=" * 60)
        print(f"URL:                {data.get('url', 'N/A')}")
        print(f"Scripts:            {len(data.get('scripts', []))}")
        print(f"Styles:             {len(data.get('styles', []))}")
        print(f"Code Blocks:        {len(data.get('code_blocks', []))}")
        print(f"Tables:             {len(data.get('tables', []))}")
        print(f"Emails:             {len(data.get('emails', []))}")
        print(f"Phone Numbers:      {len(data.get('phone_numbers', []))}")
        print(f"URLs:               {len(data.get('urls', []))}")
        print(f"Prices:             {len(data.get('prices', []))}")
        print(f"Dates:              {len(data.get('dates', []))}")
        print(f"Meta Tags:          {len(data.get('meta_tags', {}))}")
        print(f"JSON-LD:            {len(data.get('json_ld', []))}")
        print("=" * 60)

    def save_extracted(self, data: Dict, filename: str):
        """Save extracted data to JSON (path-traversal safe)"""
        try:
            path = safe_write_json(filename, data)
            print(f"✓ Saved extracted data to {path}")
        except SecurityError as e:
            print(f"✗ Security: refused to write file: {e}")


def main():
    """Main entry point for content extractor"""
    if len(sys.argv) < 2:
        print("Usage: python content_extractor.py <url> [options]")
        print("\nOptions:")
        print("  --scripts             Extract JavaScript")
        print("  --styles              Extract CSS")
        print("  --code                Extract code blocks")
        print("  --tables              Extract tables")
        print("  --emails              Extract email addresses")
        print("  --phones              Extract phone numbers")
        print("  --urls                Extract URLs")
        print("  --prices              Extract prices")
        print("  --dates               Extract dates")
        print("  --meta                Extract meta tags")
        print("  --json-ld             Extract JSON-LD")
        print("  --all                 Extract everything")
        print("  --output <file>       Save to JSON file")
        print("  --summary             Show summary only")
        sys.exit(1)

    url = sys.argv[1]
    extractor = ContentExtractor()

    extract_all = "--all" in sys.argv
    show_summary = "--summary" in sys.argv
    output_file = None

    if "--output" in sys.argv:
        output_idx = sys.argv.index("--output") + 1
        if output_idx < len(sys.argv):
            output_file = sys.argv[output_idx]

    if extract_all:
        data = extractor.extract_all(url)
    else:
        html = extractor.fetch(url)
        if not html:
            sys.exit(1)

        soup = extractor.BeautifulSoup(html, "html.parser")
        text = soup.get_text()
        data = {"url": url}

        if "--scripts" in sys.argv:
            data["scripts"] = extractor.extract_scripts(html, url)
        if "--styles" in sys.argv:
            data["styles"] = extractor.extract_styles(html, url)
        if "--code" in sys.argv:
            data["code_blocks"] = extractor.extract_code_blocks(html)
        if "--tables" in sys.argv:
            data["tables"] = extractor.extract_tables(html)
        if "--emails" in sys.argv:
            data["emails"] = extractor.extract_emails(text)
        if "--phones" in sys.argv:
            data["phone_numbers"] = extractor.extract_phone_numbers(text)
        if "--urls" in sys.argv:
            data["urls"] = extractor.extract_urls(text)
        if "--prices" in sys.argv:
            data["prices"] = extractor.extract_prices(text)
        if "--dates" in sys.argv:
            data["dates"] = extractor.extract_dates(text)
        if "--meta" in sys.argv:
            data["meta_tags"] = extractor.extract_meta_tags(html)
        if "--json-ld" in sys.argv:
            data["json_ld"] = extractor.extract_json_ld(html)

    if show_summary:
        extractor.print_summary(data)
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))

    if output_file:
        extractor.save_extracted(data, output_file)


if __name__ == "__main__":
    main()
