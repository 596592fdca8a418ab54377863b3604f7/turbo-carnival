#!/usr/bin/env python3
"""
Workflow Automation - Chain multiple web automation steps
"""

import sys
import json
import time
from typing import Dict, List, Any

try:
    from utils.security import (
        SecurityError,
        create_safe_session,
        safe_get,
        safe_write_json,
        safe_write_text,
        safe_read_json,
        safe_read_text,
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
        safe_write_text,
        safe_read_json,
        safe_read_text,
        validate_url,
    )


# Cap loop iterations to avoid runaway workflows
MAX_LOOP_ITERATIONS = 100
MAX_WAIT_SECONDS = 60
MAX_WORKFLOW_STEPS = 200


class WorkflowAutomation:
    """Execute multi-step web automation workflows"""

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

        self.context = {}
        self._step_budget = MAX_WORKFLOW_STEPS

    def execute_step(self, step: Dict) -> bool:
        """Execute a single workflow step"""
        if self._step_budget <= 0:
            print("✗ Security: workflow step budget exceeded")
            return False
        self._step_budget -= 1

        if not isinstance(step, dict):
            print("✗ Invalid step (expected object)")
            return False

        action = step.get("action")
        print(f"\n→ Executing: {action}")

        handlers = {
            "http_request": self._http_request,
            "scrape": self._scrape,
            "extract": self._extract,
            "transform": self._transform,
            "save": self._save,
            "load": self._load,
            "variable": self._variable,
            "condition": self._condition,
            "loop": self._loop,
            "wait": self._wait,
            "log": self._log,
        }

        handler = handlers.get(action)
        if not handler:
            print(f"✗ Unknown action: {action}")
            return False
        return handler(step)

    def _http_request(self, step: Dict) -> bool:
        """Execute HTTP request (SSRF-checked)"""
        url = step.get("url")
        method = step.get("method", "GET").upper()
        headers = step.get("headers", {}) or {}
        data = step.get("data", {})
        params = step.get("params", {})
        save_as = step.get("save_as")

        # Strip hop-by-hop / sensitive auth injection risks from arbitrary headers
        if not isinstance(headers, dict):
            print("  ✗ headers must be an object")
            return False
        blocked_headers = {"host", "content-length", "transfer-encoding"}
        safe_headers = {
            k: v
            for k, v in headers.items()
            if str(k).lower() not in blocked_headers
        }

        try:
            validate_url(url)
            if method == "POST":
                response = self.session.post(
                    url, headers=safe_headers, data=data, params=params, timeout=10
                )
            elif method == "PUT":
                response = self.session.put(
                    url, headers=safe_headers, data=data, params=params, timeout=10
                )
            elif method == "DELETE":
                response = self.session.delete(
                    url, headers=safe_headers, params=params, timeout=10
                )
            elif method == "GET":
                response = self.session.get(
                    url, headers=safe_headers, params=params, timeout=10
                )
            else:
                print(f"  ✗ Unsupported method: {method}")
                return False

            print(f"  Status: {response.status_code}")
            print(f"  URL: {response.url}")

            # Cap stored body size
            body = response.text
            if len(body) > 2_000_000:
                body = body[:2_000_000] + "\n…(truncated)"

            result = {
                "status_code": response.status_code,
                "headers": {
                    k: v
                    for k, v in response.headers.items()
                    if k.lower() not in ("set-cookie", "authorization")
                },
                "content": body,
                "json": None,
            }

            try:
                result["json"] = response.json()
            except (ValueError, json.JSONDecodeError):
                pass

            if save_as:
                self.context[save_as] = result
                print(f"  Saved to context: {save_as}")

            return True

        except SecurityError as e:
            print(f"  ✗ Security: {e}")
            return False
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return False

    def _scrape(self, step: Dict) -> bool:
        """Scrape web page (SSRF-checked)"""
        url = step.get("url")
        extract = step.get("extract", ["title", "links"])
        save_as = step.get("save_as")

        try:
            validate_url(url)
            response, content = safe_get(self.session, url, timeout=10)
            html = content.decode(response.encoding or "utf-8", errors="replace")
            soup = self.BeautifulSoup(html, "html.parser")

            result = {"url": url}

            if "title" in extract:
                title = soup.find("title")
                result["title"] = title.get_text().strip() if title else ""

            if "meta" in extract:
                meta = {}
                for m in soup.find_all("meta"):
                    name = m.get("name") or m.get("property")
                    content_val = m.get("content")
                    if name and content_val:
                        meta[name] = content_val
                result["meta"] = meta

            if "links" in extract:
                links = []
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if href.startswith(("javascript:", "data:", "vbscript:", "file:")):
                        continue
                    links.append({"url": href, "text": a.get_text().strip()})
                result["links"] = links

            if "text" in extract:
                for script in soup(["script", "style"]):
                    script.decompose()
                result["text"] = soup.get_text(strip=True)[:500_000]

            if save_as:
                self.context[save_as] = result
                print(f"  Saved to context: {save_as}")

            print(f"  Scraped: {url}")
            print(f"  Title: {result.get('title', 'N/A')}")
            print(f"  Links: {len(result.get('links', []))}")

            return True

        except SecurityError as e:
            print(f"  ✗ Security: {e}")
            return False
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return False

    def _extract(self, step: Dict) -> bool:
        """Extract data from context"""
        from_var = step.get("from")
        path = step.get("path")
        save_as = step.get("save_as")

        if from_var not in self.context:
            print(f"  ✗ Variable not found: {from_var}")
            return False

        data = self.context[from_var]

        if path:
            for key in path.split("."):
                if isinstance(data, dict):
                    data = data.get(key)
                elif isinstance(data, list) and key.isdigit():
                    idx = int(key)
                    if idx < 0 or idx >= len(data):
                        print(f"  ✗ Invalid path index: {path}")
                        return False
                    data = data[idx]
                else:
                    print(f"  ✗ Invalid path: {path}")
                    return False

        if save_as:
            self.context[save_as] = data
            print(f"  Extracted to {save_as}: {str(data)[:100]}")

        return True

    def _transform(self, step: Dict) -> bool:
        """Transform data"""
        from_var = step.get("from")
        operation = step.get("operation")
        save_as = step.get("save_as")

        if from_var not in self.context:
            print(f"  ✗ Variable not found: {from_var}")
            return False

        data = self.context[from_var]
        result = data

        if operation == "filter":
            field = step.get("field")
            value = step.get("value")
            if isinstance(data, list):
                result = [
                    item
                    for item in data
                    if isinstance(item, dict) and str(item.get(field)) == str(value)
                ]

        elif operation == "map":
            field = step.get("field")
            if isinstance(data, list):
                result = [
                    item.get(field)
                    for item in data
                    if isinstance(item, dict) and field in item
                ]

        elif operation == "count":
            if isinstance(data, (list, dict)):
                result = len(data)

        elif operation == "first":
            if isinstance(data, list) and data:
                result = data[0]

        elif operation == "last":
            if isinstance(data, list) and data:
                result = data[-1]

        elif operation == "unique":
            if isinstance(data, list):
                # Fixed: set() crashes on unhashable dict items
                seen = []
                unique = []
                for item in data:
                    try:
                        key = json.dumps(item, sort_keys=True, default=str)
                    except (TypeError, ValueError):
                        key = str(item)
                    if key not in seen:
                        seen.append(key)
                        unique.append(item)
                result = unique

        if save_as:
            self.context[save_as] = result
            print(f"  Transformed to {save_as}")

        return True

    def _save(self, step: Dict) -> bool:
        """Save data to file (path-traversal safe)"""
        from_var = step.get("from")
        filename = step.get("filename")
        format_type = step.get("format", "json")

        if from_var not in self.context:
            print(f"  ✗ Variable not found: {from_var}")
            return False

        data = self.context[from_var]

        try:
            if format_type == "json":
                path = safe_write_json(filename, data)
            elif format_type == "text":
                path = safe_write_text(filename, str(data))
            else:
                print(f"  ✗ Unsupported format: {format_type}")
                return False

            print(f"  Saved to {path}")
            return True

        except SecurityError as e:
            print(f"  ✗ Security: {e}")
            return False
        except Exception as e:
            print(f"  ✗ Error saving: {e}")
            return False

    def _load(self, step: Dict) -> bool:
        """Load data from file (path-traversal safe)"""
        filename = step.get("filename")
        save_as = step.get("save_as")
        format_type = step.get("format", "json")

        try:
            if format_type == "json":
                data = safe_read_json(filename)
            else:
                data = safe_read_text(filename)

            if save_as:
                self.context[save_as] = data
                print(f"  Loaded from {filename} to {save_as}")

            return True

        except SecurityError as e:
            print(f"  ✗ Security: {e}")
            return False
        except Exception as e:
            print(f"  ✗ Error loading: {e}")
            return False

    def _variable(self, step: Dict) -> bool:
        """Set variable"""
        name = step.get("name")
        value = step.get("value")
        if not name or not isinstance(name, str):
            print("  ✗ Invalid variable name")
            return False
        self.context[name] = value
        print(f"  Set {name} = {value}")
        return True

    def _condition(self, step: Dict) -> bool:
        """Conditional execution"""
        condition = step.get("if")
        then_steps = step.get("then", []) or []
        else_steps = step.get("else", []) or []

        if not isinstance(condition, str):
            print("  ✗ Invalid condition")
            return False

        # Simple equality check only (no eval)
        if "=" in condition:
            var, val = condition.split("=", 1)
            var = var.strip()
            val = val.strip()
            result = str(self.context.get(var, "")) == val
        else:
            result = bool(self.context.get(condition))

        branch = then_steps if result else else_steps
        print(f"  Condition {'true' if result else 'false'}: {condition}")
        for nested in branch:
            if not self.execute_step(nested):
                return False

        return True

    def _loop(self, step: Dict) -> bool:
        """Loop over steps (capped)"""
        from_var = step.get("over")
        steps = step.get("steps", []) or []

        if from_var not in self.context:
            print(f"  ✗ Variable not found: {from_var}")
            return False

        data = self.context[from_var]

        if not isinstance(data, list):
            print(f"  ✗ Variable is not a list: {from_var}")
            return False

        items = data[:MAX_LOOP_ITERATIONS]
        if len(data) > MAX_LOOP_ITERATIONS:
            print(
                f"  ⚠ Loop truncated to {MAX_LOOP_ITERATIONS} "
                f"of {len(data)} items"
            )

        print(f"  Looping over {len(items)} items")

        for idx, item in enumerate(items):
            self.context["item"] = item
            self.context["index"] = idx
            print(f"\n  → Iteration {idx + 1}/{len(items)}")

            for nested in steps:
                if not self.execute_step(nested):
                    return False

        return True

    def _wait(self, step: Dict) -> bool:
        """Wait for specified time (capped)"""
        try:
            seconds = float(step.get("seconds", 1))
        except (TypeError, ValueError):
            print("  ✗ Invalid wait seconds")
            return False
        seconds = max(0.0, min(seconds, MAX_WAIT_SECONDS))
        print(f"  Waiting {seconds} seconds...")
        time.sleep(seconds)
        return True

    def _log(self, step: Dict) -> bool:
        """Log message"""
        message = step.get("message", "")
        from_var = step.get("from")

        if from_var:
            value = self.context.get(from_var, "")
            print(f"  LOG: {message} {value}")
        else:
            print(f"  LOG: {message}")

        return True

    def execute_workflow(self, workflow: List[Dict]) -> bool:
        """Execute complete workflow"""
        if not isinstance(workflow, list):
            print("✗ Workflow must be a JSON array")
            return False

        if len(workflow) > MAX_WORKFLOW_STEPS:
            print(
                f"✗ Security: workflow has {len(workflow)} steps; "
                f"max is {MAX_WORKFLOW_STEPS}"
            )
            return False

        self._step_budget = MAX_WORKFLOW_STEPS

        print("=" * 60)
        print("WORKFLOW EXECUTION")
        print("=" * 60)
        print(f"Steps: {len(workflow)}")

        for idx, step in enumerate(workflow, 1):
            print(f"\n[Step {idx}/{len(workflow)}]")
            if not self.execute_step(step):
                print(f"\n✗ Workflow failed at step {idx}")
                return False

        print("\n" + "=" * 60)
        print("✓ Workflow completed successfully")
        print("=" * 60)
        return True

    def print_context(self):
        """Print current context"""
        print("\nCurrent Context:")
        print("-" * 60)
        for key, value in self.context.items():
            if isinstance(value, (list, dict)):
                print(f"  {key}: {type(value).__name__} ({len(value)} items)")
            else:
                print(f"  {key}: {str(value)[:100]}")


def main():
    """Main entry point for workflow automation"""
    if len(sys.argv) < 2:
        print("Usage: python workflow_automation.py <workflow_file.json>")
        print("\nWorkflow file format:")
        print(
            json.dumps(
                [
                    {
                        "action": "variable",
                        "name": "base_url",
                        "value": "https://example.com",
                    },
                    {
                        "action": "scrape",
                        "url": "https://example.com",
                        "save_as": "page_data",
                    },
                    {
                        "action": "extract",
                        "from": "page_data",
                        "path": "links",
                        "save_as": "links",
                    },
                    {
                        "action": "save",
                        "from": "links",
                        "filename": "links.json",
                    },
                ],
                indent=2,
            )
        )
        sys.exit(1)

    workflow_file = sys.argv[1]

    try:
        workflow = safe_read_json(workflow_file)
    except (SecurityError, OSError, json.JSONDecodeError) as e:
        print(f"✗ Error loading workflow file: {e}")
        sys.exit(1)

    automation = WorkflowAutomation()
    success = automation.execute_workflow(workflow)

    if "--context" in sys.argv:
        automation.print_context()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
