#!/usr/bin/env python3
"""
Web Insights Analyzer - Analyze websites for SEO, performance, and structure
"""

import sys
from typing import Dict
from urllib.parse import urlparse

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


class WebInsightsAnalyzer:
    """Analyze websites and provide insights"""

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

    def analyze_seo(self, html: str, url: str) -> Dict:
        """Analyze SEO elements"""
        soup = self.BeautifulSoup(html, "html.parser")
        insights = {
            "title": {"found": False, "length": 0, "issues": []},
            "meta_description": {"found": False, "length": 0, "issues": []},
            "headings": {"h1": 0, "h2": 0, "h3": 0, "issues": []},
            "images": {"total": 0, "without_alt": 0, "issues": []},
            "links": {"total": 0, "broken": 0, "issues": []},
        }

        title = soup.find("title")
        if title:
            insights["title"]["found"] = True
            insights["title"]["length"] = len(title.get_text())
            if insights["title"]["length"] < 30:
                insights["title"]["issues"].append("Title too short (< 30 chars)")
            elif insights["title"]["length"] > 60:
                insights["title"]["issues"].append("Title too long (> 60 chars)")
        else:
            insights["title"]["issues"].append("Missing title tag")

        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            insights["meta_description"]["found"] = True
            content = meta_desc.get("content", "")
            insights["meta_description"]["length"] = len(content)
            if insights["meta_description"]["length"] < 120:
                insights["meta_description"]["issues"].append(
                    "Description too short (< 120 chars)"
                )
            elif insights["meta_description"]["length"] > 160:
                insights["meta_description"]["issues"].append(
                    "Description too long (> 160 chars)"
                )
        else:
            insights["meta_description"]["issues"].append("Missing meta description")

        h1_tags = soup.find_all("h1")
        insights["headings"]["h1"] = len(h1_tags)
        if len(h1_tags) == 0:
            insights["headings"]["issues"].append("Missing H1 tag")
        elif len(h1_tags) > 1:
            insights["headings"]["issues"].append(
                "Multiple H1 tags (should have only one)"
            )

        insights["headings"]["h2"] = len(soup.find_all("h2"))
        insights["headings"]["h3"] = len(soup.find_all("h3"))

        images = soup.find_all("img")
        insights["images"]["total"] = len(images)
        for img in images:
            if not img.get("alt"):
                insights["images"]["without_alt"] += 1

        if insights["images"]["without_alt"] > 0:
            insights["images"]["issues"].append(
                f'{insights["images"]["without_alt"]} images missing alt text'
            )

        links = soup.find_all("a", href=True)
        insights["links"]["total"] = len(links)

        return insights

    def analyze_performance(self, url: str) -> Dict:
        """Analyze basic performance metrics"""
        insights = {
            "response_time": 0,
            "page_size": 0,
            "requests": 0,
            "issues": [],
        }

        try:
            import time

            validate_url(url)
            start_time = time.time()
            response, content = safe_get(self.session, url, timeout=10)
            end_time = time.time()

            insights["response_time"] = round((end_time - start_time) * 1000, 2)
            insights["page_size"] = len(content)
            insights["status_code"] = response.status_code

            if insights["response_time"] > 2000:
                insights["issues"].append(
                    f'Slow response time ({insights["response_time"]}ms)'
                )
            if insights["page_size"] > 2_000_000:
                insights["issues"].append(
                    f'Large page size ({insights["page_size"] / 1024 / 1024:.2f}MB)'
                )

        except SecurityError as e:
            insights["issues"].append(f"Security block: {e}")
        except Exception as e:
            insights["issues"].append(f"Performance check failed: {e}")

        return insights

    def analyze_structure(self, html: str) -> Dict:
        """Analyze HTML structure"""
        soup = self.BeautifulSoup(html, "html.parser")
        insights = {
            "html5": False,
            "has_semantic_tags": False,
            "script_count": 0,
            "style_count": 0,
            "external_resources": 0,
            "issues": [],
        }

        stripped = html.lstrip()
        if stripped.lower().startswith("<!doctype html>"):
            insights["html5"] = True
        else:
            insights["issues"].append("Missing HTML5 doctype")

        semantic_tags = ["header", "nav", "main", "article", "section", "aside", "footer"]
        for tag in semantic_tags:
            if soup.find(tag):
                insights["has_semantic_tags"] = True
                break

        if not insights["has_semantic_tags"]:
            insights["issues"].append("No semantic HTML tags found")

        insights["script_count"] = len(soup.find_all("script"))
        insights["style_count"] = len(soup.find_all("style")) + len(
            soup.find_all("link", rel="stylesheet")
        )

        for tag in soup.find_all(["link", "script", "img"]):
            href = tag.get("href") or ""
            src = tag.get("src") or ""
            if href.startswith("http") or src.startswith("http"):
                insights["external_resources"] += 1

        if insights["script_count"] > 10:
            insights["issues"].append(f'Many scripts ({insights["script_count"]})')

        return insights

    def analyze_security(self, html: str, url: str) -> Dict:
        """Analyze basic security aspects"""
        insights = {
            "https": False,
            "has_mixed_content": False,
            "has_insecure_forms": False,
            "issues": [],
        }

        parsed_url = urlparse(url)
        insights["https"] = parsed_url.scheme == "https"

        if not insights["https"]:
            insights["issues"].append("Not using HTTPS")

        soup = self.BeautifulSoup(html, "html.parser")
        if insights["https"]:
            for tag in soup.find_all(["img", "script", "link"]):
                src = tag.get("src") or tag.get("href")
                if src and src.startswith("http://"):
                    insights["has_mixed_content"] = True
                    insights["issues"].append(
                        "Mixed content detected (HTTP resources on HTTPS page)"
                    )
                    break

        for form in soup.find_all("form"):
            action = form.get("action", "")
            if action.startswith("http://"):
                insights["has_insecure_forms"] = True
                insights["issues"].append("Insecure form action (HTTP)")
                break

        return insights

    def analyze_content(self, html: str) -> Dict:
        """Analyze content quality"""
        soup = self.BeautifulSoup(html, "html.parser")

        for script in soup(["script", "style"]):
            script.decompose()

        text = soup.get_text()
        words = text.split()

        insights = {
            "word_count": len(words),
            "paragraph_count": len(
                [p for p in soup.find_all("p") if p.get_text().strip()]
            ),
            "reading_time_minutes": len(words) // 200,
            "issues": [],
        }

        if insights["word_count"] < 300:
            insights["issues"].append(
                "Low word count (consider adding more content)"
            )

        return insights

    def analyze_accessibility(self, html: str) -> Dict:
        """Analyze basic accessibility"""
        soup = self.BeautifulSoup(html, "html.parser")
        insights = {
            "has_lang_attribute": False,
            "images_with_alt": 0,
            "images_without_alt": 0,
            "form_labels": 0,
            "issues": [],
        }

        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            insights["has_lang_attribute"] = True
        else:
            insights["issues"].append("Missing lang attribute on html tag")

        for img in soup.find_all("img"):
            if img.get("alt") is not None and img.get("alt") != "":
                insights["images_with_alt"] += 1
            elif img.get("alt") == "":
                # Empty alt can be intentional for decorative images
                insights["images_with_alt"] += 1
            else:
                insights["images_without_alt"] += 1

        if insights["images_without_alt"] > 0:
            insights["issues"].append(
                f'{insights["images_without_alt"]} images without alt text'
            )

        for inp in soup.find_all("input"):
            if inp.get("id"):
                label = soup.find("label", attrs={"for": inp.get("id")})
                if label:
                    insights["form_labels"] += 1

        return insights

    def full_analysis(self, url: str) -> Dict:
        """Perform complete website analysis"""
        print(f"Analyzing {url}...")

        html = self.fetch(url)
        if not html:
            return {"error": "Failed to fetch page"}

        return {
            "url": url,
            "seo": self.analyze_seo(html, url),
            "performance": self.analyze_performance(url),
            "structure": self.analyze_structure(html),
            "security": self.analyze_security(html, url),
            "content": self.analyze_content(html),
            "accessibility": self.analyze_accessibility(html),
        }

    def print_report(self, analysis: Dict):
        """Print analysis report (safe for partial analyses)"""
        print("\n" + "=" * 70)
        print("WEB INSIGHTS REPORT")
        print("=" * 70)
        print(f"URL: {analysis.get('url', 'N/A')}")

        seo = analysis.get("seo")
        if seo:
            print("\n📊 SEO ANALYSIS")
            print("-" * 70)
            print(f"Title: {'✓' if seo['title']['found'] else '✗'} Found")
            print(f"  Length: {seo['title']['length']} chars")
            if seo["title"]["issues"]:
                print("  Issues:", ", ".join(seo["title"]["issues"]))

            print(
                f"\nMeta Description: "
                f"{'✓' if seo['meta_description']['found'] else '✗'} Found"
            )
            print(f"  Length: {seo['meta_description']['length']} chars")
            if seo["meta_description"]["issues"]:
                print("  Issues:", ", ".join(seo["meta_description"]["issues"]))

            print(
                f"\nHeadings: H1={seo['headings']['h1']}, "
                f"H2={seo['headings']['h2']}, H3={seo['headings']['h3']}"
            )
            if seo["headings"]["issues"]:
                print("  Issues:", ", ".join(seo["headings"]["issues"]))

            print(
                f"\nImages: {seo['images']['total']} total, "
                f"{seo['images']['without_alt']} without alt"
            )
            if seo["images"]["issues"]:
                print("  Issues:", ", ".join(seo["images"]["issues"]))

        perf = analysis.get("performance")
        if perf:
            print("\n⚡ PERFORMANCE")
            print("-" * 70)
            print(f"Response Time: {perf.get('response_time', 0)}ms")
            print(f"Page Size: {perf.get('page_size', 0) / 1024:.2f}KB")
            print(f"Status Code: {perf.get('status_code', 'N/A')}")
            if perf.get("issues"):
                print("Issues:", ", ".join(perf["issues"]))

        struct = analysis.get("structure")
        if struct:
            print("\n🏗️  STRUCTURE")
            print("-" * 70)
            print(f"HTML5: {'✓' if struct['html5'] else '✗'}")
            print(f"Semantic Tags: {'✓' if struct['has_semantic_tags'] else '✗'}")
            print(f"Scripts: {struct['script_count']}")
            print(f"Styles: {struct['style_count']}")
            print(f"External Resources: {struct['external_resources']}")
            if struct.get("issues"):
                print("Issues:", ", ".join(struct["issues"]))

        sec = analysis.get("security")
        if sec:
            print("\n🔒 SECURITY")
            print("-" * 70)
            print(f"HTTPS: {'✓' if sec['https'] else '✗'}")
            # Fixed misleading labels: True used to print as ✓ for bad states
            print(
                f"Mixed Content: "
                f"{'✗ Detected' if sec['has_mixed_content'] else '✓ None'}"
            )
            print(
                f"Insecure Forms: "
                f"{'✗ Detected' if sec['has_insecure_forms'] else '✓ None'}"
            )
            if sec.get("issues"):
                print("Issues:", ", ".join(sec["issues"]))

        content = analysis.get("content")
        if content:
            print("\n📝 CONTENT")
            print("-" * 70)
            print(f"Word Count: {content['word_count']}")
            print(f"Paragraph Count: {content['paragraph_count']}")
            print(f"Est. Reading Time: {content['reading_time_minutes']} min")
            if content.get("issues"):
                print("Issues:", ", ".join(content["issues"]))

        a11y = analysis.get("accessibility")
        if a11y:
            print("\n♿ ACCESSIBILITY")
            print("-" * 70)
            print(f"Lang Attribute: {'✓' if a11y['has_lang_attribute'] else '✗'}")
            print(f"Images with Alt: {a11y['images_with_alt']}")
            print(f"Images without Alt: {a11y['images_without_alt']}")
            print(f"Form Labels: {a11y['form_labels']}")
            if a11y.get("issues"):
                print("Issues:", ", ".join(a11y["issues"]))

        print("\n" + "=" * 70)

    def get_score(self, analysis: Dict) -> Dict:
        """Calculate overall scores (skips missing sections)"""
        scores = {}

        seo = analysis.get("seo")
        if seo:
            scores["seo"] = 100
            if not seo["title"]["found"]:
                scores["seo"] -= 20
            if not seo["meta_description"]["found"]:
                scores["seo"] -= 20
            if seo["headings"]["h1"] == 0:
                scores["seo"] -= 10
            if seo["images"]["without_alt"] > 0:
                scores["seo"] -= min(20, seo["images"]["without_alt"] * 2)

        perf = analysis.get("performance")
        if perf:
            scores["performance"] = 100
            if perf.get("response_time", 0) > 2000:
                scores["performance"] -= 30
            elif perf.get("response_time", 0) > 1000:
                scores["performance"] -= 15

        struct = analysis.get("structure")
        if struct:
            scores["structure"] = 100
            if not struct["html5"]:
                scores["structure"] -= 20
            if not struct["has_semantic_tags"]:
                scores["structure"] -= 10

        sec = analysis.get("security")
        if sec:
            scores["security"] = 100
            if not sec["https"]:
                scores["security"] -= 50
            if sec["has_mixed_content"]:
                scores["security"] -= 20
            if sec["has_insecure_forms"]:
                scores["security"] -= 20

        a11y = analysis.get("accessibility")
        if a11y:
            scores["accessibility"] = 100
            if not a11y["has_lang_attribute"]:
                scores["accessibility"] -= 20
            if a11y["images_without_alt"] > 0:
                scores["accessibility"] -= min(30, a11y["images_without_alt"] * 3)

        if scores:
            scores["overall"] = round(sum(scores.values()) / len(scores), 1)
        else:
            scores["overall"] = 0.0

        return scores


def main():
    """Main entry point for web insights analyzer"""
    if len(sys.argv) < 2:
        print("Usage: python web_insights.py <url> [options]")
        print("\nOptions:")
        print("  --seo                 Analyze SEO only")
        print("  --performance         Analyze performance only")
        print("  --structure           Analyze structure only")
        print("  --security            Analyze security only")
        print("  --content             Analyze content only")
        print("  --accessibility       Analyze accessibility only")
        print("  --score               Show scores")
        print("  --output <file>       Save report to JSON")
        sys.exit(1)

    url = sys.argv[1]
    analyzer = WebInsightsAnalyzer()

    seo_only = "--seo" in sys.argv
    perf_only = "--performance" in sys.argv
    struct_only = "--structure" in sys.argv
    sec_only = "--security" in sys.argv
    content_only = "--content" in sys.argv
    a11y_only = "--accessibility" in sys.argv
    show_score = "--score" in sys.argv
    output_file = None

    if "--output" in sys.argv:
        output_idx = sys.argv.index("--output") + 1
        if output_idx < len(sys.argv):
            output_file = sys.argv[output_idx]

    flags = [seo_only, perf_only, struct_only, sec_only, content_only, a11y_only]
    run_all = not any(flags)

    html = analyzer.fetch(url)
    if not html:
        sys.exit(1)

    analysis = {"url": url}

    if seo_only or run_all:
        analysis["seo"] = analyzer.analyze_seo(html, url)
    if perf_only or run_all:
        analysis["performance"] = analyzer.analyze_performance(url)
    if struct_only or run_all:
        analysis["structure"] = analyzer.analyze_structure(html)
    if sec_only or run_all:
        analysis["security"] = analyzer.analyze_security(html, url)
    if content_only or run_all:
        analysis["content"] = analyzer.analyze_content(html)
    if a11y_only or run_all:
        analysis["accessibility"] = analyzer.analyze_accessibility(html)

    analyzer.print_report(analysis)

    if show_score:
        scores = analyzer.get_score(analysis)
        print("\n📈 SCORES")
        print("-" * 70)
        for category, score in scores.items():
            if category != "overall":
                status = "✓" if score >= 80 else "⚠" if score >= 60 else "✗"
                print(f"{status} {category.capitalize():15} {score}/100")
        print(f"\nOverall Score: {scores['overall']}/100")

    if output_file:
        try:
            path = safe_write_json(output_file, analysis)
            print(f"\n✓ Report saved to {path}")
        except SecurityError as e:
            print(f"\n✗ Security: refused to write file: {e}")


if __name__ == "__main__":
    main()
