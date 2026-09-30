#!/usr/bin/env python3
"""
Browser Automation - Control browsers (headless/headed) from terminal
"""

import sys
import json
from typing import Dict, List

try:
    from utils.security import (
        SecurityError,
        safe_output_path,
        safe_read_json,
        validate_url,
        redact_value,
    )
except ImportError:
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from utils.security import (
        SecurityError,
        safe_output_path,
        safe_read_json,
        validate_url,
        redact_value,
    )


# Actions allowed in browser workflows (no arbitrary evaluate by default)
ALLOWED_WORKFLOW_ACTIONS = frozenset(
    {
        "navigate",
        "click",
        "fill",
        "select",
        "wait",
        "wait_for",
        "screenshot",
        "scroll",
    }
)


class BrowserAutomation:
    """Browser automation using Playwright"""

    def __init__(self, headless: bool = True, allow_evaluate: bool = False):
        self.headless = headless
        self.allow_evaluate = allow_evaluate
        self.browser = None
        self.page = None
        self.playwright = None

        try:
            from playwright.sync_api import sync_playwright
            self.sync_playwright = sync_playwright
        except ImportError:
            print("✗ Error: Playwright not installed")
            print("Install with: pip install playwright")
            print("Then run: playwright install")
            sys.exit(1)

    def start(self):
        """Start browser instance"""
        self.playwright = self.sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()
        print(f"✓ Browser started (headless: {self.headless})")

    def close(self):
        """Close browser instance"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        print("✓ Browser closed")

    def navigate(self, url: str) -> bool:
        """Navigate to URL (SSRF-checked)"""
        try:
            validate_url(url)
            self.page.goto(url, wait_until="networkidle", timeout=30000)
            print(f"✓ Navigated to {url}")
            return True
        except SecurityError as e:
            print(f"✗ Security: blocked navigation to {url}: {e}")
            return False
        except Exception as e:
            print(f"✗ Error navigating to {url}: {e}")
            return False

    def screenshot(self, filename: str, full_page: bool = False):
        """Take screenshot (path confined to cwd)"""
        try:
            path = safe_output_path(
                filename,
                allowed_suffixes={".png", ".jpg", ".jpeg", ".webp"},
            )
            self.page.screenshot(path=str(path), full_page=full_page)
            print(f"✓ Screenshot saved to {path}")
        except SecurityError as e:
            print(f"✗ Security: refused screenshot path: {e}")
        except Exception as e:
            print(f"✗ Error taking screenshot: {e}")

    def get_title(self) -> str:
        """Get page title"""
        return self.page.title()

    def get_url(self) -> str:
        """Get current URL"""
        return self.page.url

    def get_content(self) -> str:
        """Get page content"""
        return self.page.content()

    def click(self, selector: str) -> bool:
        """Click element"""
        try:
            self.page.click(selector)
            print(f"✓ Clicked {selector}")
            return True
        except Exception as e:
            print(f"✗ Error clicking {selector}: {e}")
            return False

    def fill(self, selector: str, value: str) -> bool:
        """Fill input field (does not log secret values)"""
        try:
            self.page.fill(selector, value)
            shown = redact_value(selector, value)
            print(f"✓ Filled {selector} with '{shown}'")
            return True
        except Exception as e:
            print(f"✗ Error filling {selector}: {e}")
            return False

    def select_option(self, selector: str, value: str) -> bool:
        """Select dropdown option"""
        try:
            self.page.select_option(selector, value)
            print(f"✓ Selected '{value}' in {selector}")
            return True
        except Exception as e:
            print(f"✗ Error selecting option: {e}")
            return False

    def wait_for_selector(self, selector: str, timeout: int = 5000) -> bool:
        """Wait for selector to appear"""
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            print(f"✓ Element {selector} appeared")
            return True
        except Exception as e:
            print(f"✗ Timeout waiting for {selector}: {e}")
            return False

    def wait_for_navigation(self, timeout: int = 5000) -> bool:
        """Wait for navigation to complete"""
        try:
            self.page.wait_for_load_state("networkidle", timeout=timeout)
            print("✓ Navigation completed")
            return True
        except Exception as e:
            print(f"✗ Timeout waiting for navigation: {e}")
            return False

    def evaluate(self, script: str):
        """Execute JavaScript in page (disabled unless explicitly allowed)"""
        if not self.allow_evaluate:
            print(
                "✗ Security: JavaScript evaluate is disabled. "
                "Pass --allow-evaluate to enable (trusted pages only)."
            )
            return None
        try:
            result = self.page.evaluate(script)
            print("✓ Executed JavaScript")
            return result
        except Exception as e:
            print(f"✗ Error executing JavaScript: {e}")
            return None

    def get_text(self, selector: str) -> str:
        """Get text content of element"""
        try:
            return self.page.inner_text(selector)
        except Exception as e:
            print(f"✗ Error getting text from {selector}: {e}")
            return ""

    def get_attribute(self, selector: str, attribute: str) -> str:
        """Get attribute value of element"""
        try:
            return self.page.get_attribute(selector, attribute) or ""
        except Exception as e:
            print(f"✗ Error getting attribute {attribute} from {selector}: {e}")
            return ""

    def extract_links(self) -> List[Dict]:
        """Extract all links from page"""
        links = []
        elements = self.page.query_selector_all("a")

        for element in elements:
            href = element.get_attribute("href")
            text = element.inner_text()
            if href and not href.startswith(("javascript:", "data:", "vbscript:")):
                links.append({"url": href, "text": (text or "").strip()})

        print(f"✓ Extracted {len(links)} links")
        return links

    def extract_forms(self) -> List[Dict]:
        """Extract all forms from page"""
        forms = []
        elements = self.page.query_selector_all("form")

        for idx, form in enumerate(elements):
            action = form.get_attribute("action") or ""
            method = form.get_attribute("method") or "GET"

            inputs = form.query_selector_all("input")
            fields = []
            for inp in inputs:
                name = inp.get_attribute("name") or ""
                fields.append(
                    {
                        "type": inp.get_attribute("type") or "text",
                        "name": name,
                        "id": inp.get_attribute("id") or "",
                    }
                )

            forms.append(
                {
                    "index": idx,
                    "action": action,
                    "method": method.upper(),
                    "fields": fields,
                }
            )

        print(f"✓ Extracted {len(forms)} forms")
        return forms

    def scroll_to_bottom(self):
        """Scroll to bottom of page"""
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        print("✓ Scrolled to bottom")

    def set_viewport_size(self, width: int, height: int):
        """Set viewport size"""
        self.page.set_viewport_size({"width": width, "height": height})
        print(f"✓ Set viewport to {width}x{height}")

    def set_user_agent(self, user_agent: str):
        """Set custom user agent"""
        self.page.set_extra_http_headers({"User-Agent": user_agent})
        print("✓ Set user agent")

    def execute_script(self, workflow: List[Dict]) -> bool:
        """Execute a workflow of actions (no arbitrary JS)"""
        print(f"\nExecuting workflow with {len(workflow)} steps...")

        for step in workflow:
            if not isinstance(step, dict):
                print("✗ Invalid workflow step (expected object)")
                return False

            action = step.get("action")
            selector = step.get("selector")
            value = step.get("value")

            if action not in ALLOWED_WORKFLOW_ACTIONS:
                print(
                    f"✗ Security: action '{action}' is not allowed in "
                    "browser workflows"
                )
                return False

            if action == "navigate":
                if not self.navigate(value):
                    return False

            elif action == "click":
                if not self.click(selector):
                    return False

            elif action == "fill":
                if not self.fill(selector, value if value is not None else ""):
                    return False

            elif action == "select":
                if not self.select_option(selector, value):
                    return False

            elif action == "wait":
                import time

                try:
                    seconds = float(value)
                except (TypeError, ValueError):
                    print("✗ Invalid wait value")
                    return False
                # Cap wait to avoid accidental hangs
                seconds = max(0.0, min(seconds, 60.0))
                time.sleep(seconds)
                print(f"✓ Waited {seconds} seconds")

            elif action == "wait_for":
                if not self.wait_for_selector(selector):
                    return False

            elif action == "screenshot":
                self.screenshot(value)

            elif action == "scroll":
                self.scroll_to_bottom()

        print("✓ Workflow completed successfully")
        return True


def main():
    """Main entry point for browser automation"""
    if len(sys.argv) < 2:
        print("Usage: python browser_automation.py <url> [options]")
        print("\nOptions:")
        print("  --headed               Run with visible browser (default: headless)")
        print("  --screenshot <file>    Take screenshot")
        print("  --full-page            Full page screenshot")
        print("  --click <selector>     Click element")
        print("  --fill <selector> <value>  Fill input field")
        print("  --select <selector> <value>  Select dropdown")
        print("  --wait <seconds>       Wait for N seconds")
        print("  --workflow <file>      Execute workflow from JSON file")
        print("  --extract-links        Extract all links")
        print("  --extract-forms        Extract all forms")
        print("  --evaluate <script>    Execute JavaScript (requires --allow-evaluate)")
        print("  --allow-evaluate       Enable page.evaluate (trusted use only)")
        sys.exit(1)

    url = sys.argv[1]
    headless = "--headed" not in sys.argv
    allow_evaluate = "--allow-evaluate" in sys.argv

    automation = BrowserAutomation(headless=headless, allow_evaluate=allow_evaluate)
    automation.start()

    try:
        if not automation.navigate(url):
            sys.exit(1)

        if "--screenshot" in sys.argv:
            screenshot_idx = sys.argv.index("--screenshot") + 1
            if screenshot_idx < len(sys.argv):
                filename = sys.argv[screenshot_idx]
                full_page = "--full-page" in sys.argv
                automation.screenshot(filename, full_page)

        if "--click" in sys.argv:
            click_idx = sys.argv.index("--click") + 1
            if click_idx < len(sys.argv):
                automation.click(sys.argv[click_idx])

        if "--fill" in sys.argv:
            fill_idx = sys.argv.index("--fill") + 1
            if fill_idx + 1 < len(sys.argv):
                selector = sys.argv[fill_idx]
                value = sys.argv[fill_idx + 1]
                automation.fill(selector, value)

        if "--select" in sys.argv:
            select_idx = sys.argv.index("--select") + 1
            if select_idx + 1 < len(sys.argv):
                selector = sys.argv[select_idx]
                value = sys.argv[select_idx + 1]
                automation.select_option(selector, value)

        if "--wait" in sys.argv:
            wait_idx = sys.argv.index("--wait") + 1
            if wait_idx < len(sys.argv):
                import time

                try:
                    seconds = max(0.0, min(float(sys.argv[wait_idx]), 60.0))
                except ValueError:
                    print("✗ Error: --wait must be a number")
                    sys.exit(1)
                time.sleep(seconds)

        if "--workflow" in sys.argv:
            workflow_idx = sys.argv.index("--workflow") + 1
            if workflow_idx < len(sys.argv):
                try:
                    workflow = safe_read_json(sys.argv[workflow_idx])
                    if not isinstance(workflow, list):
                        print("✗ Workflow file must be a JSON array of steps")
                        sys.exit(1)
                    automation.execute_script(workflow)
                except (SecurityError, OSError, json.JSONDecodeError) as e:
                    print(f"✗ Error loading workflow: {e}")
                    sys.exit(1)

        if "--extract-links" in sys.argv:
            links = automation.extract_links()
            print(f"\nLinks ({len(links)}):")
            for link in links[:20]:
                print(f"  {link['text'][:50]:<50} {link['url']}")

        if "--extract-forms" in sys.argv:
            forms = automation.extract_forms()
            print(f"\nForms ({len(forms)}):")
            for form in forms:
                print(f"  Form {form['index']}: {form['method']} {form['action']}")

        if "--evaluate" in sys.argv:
            eval_idx = sys.argv.index("--evaluate") + 1
            if eval_idx < len(sys.argv):
                result = automation.evaluate(sys.argv[eval_idx])
                if result is not None:
                    print(f"Result: {result}")

        print("\nPage Info:")
        print(f"  Title: {automation.get_title()}")
        print(f"  URL:   {automation.get_url()}")

    finally:
        automation.close()


if __name__ == "__main__":
    main()
