#!/usr/bin/env python3
"""
Form Automation - Automate web form submissions from terminal
"""

import sys
import json
from typing import Dict, List
from urllib.parse import urljoin

try:
    from utils.security import (
        SecurityError,
        create_safe_session,
        safe_get,
        safe_read_json,
        validate_url,
        is_sensitive_field_name,
        redact_value,
    )
except ImportError:
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from utils.security import (
        SecurityError,
        create_safe_session,
        safe_get,
        safe_read_json,
        validate_url,
        is_sensitive_field_name,
        redact_value,
    )


class FormAutomation:
    """Automate web form interactions"""

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

    def extract_forms(self, html: str, base_url: str) -> List[Dict]:
        """Extract all forms from page"""
        soup = self.BeautifulSoup(html, "html.parser")
        forms = []

        for idx, form in enumerate(soup.find_all("form")):
            form_data = {
                "index": idx,
                "action": urljoin(base_url, form.get("action", "") or base_url),
                "method": form.get("method", "GET").upper(),
                "fields": [],
            }

            for input_field in form.find_all("input"):
                field_type = input_field.get("type", "text") or "text"
                # Never capture password/default secret values from HTML
                raw_value = input_field.get("value", "")
                if is_sensitive_field_name(
                    input_field.get("name", "")
                ) or field_type.lower() in ("password", "hidden"):
                    # Keep hidden non-secret tokens (CSRF) but redact password-like
                    if field_type.lower() == "password" or is_sensitive_field_name(
                        input_field.get("name", "")
                    ):
                        raw_value = ""
                field = {
                    "type": field_type,
                    "name": input_field.get("name", ""),
                    "value": raw_value,
                    "id": input_field.get("id", ""),
                    "required": input_field.has_attr("required"),
                }
                if field["name"] or field["id"]:
                    form_data["fields"].append(field)

            for textarea in form.find_all("textarea"):
                field = {
                    "type": "textarea",
                    "name": textarea.get("name", ""),
                    "value": textarea.get_text(strip=True),
                    "id": textarea.get("id", ""),
                    "required": textarea.has_attr("required"),
                }
                if field["name"] or field["id"]:
                    form_data["fields"].append(field)

            for select in form.find_all("select"):
                options = []
                for option in select.find_all("option"):
                    options.append(
                        {
                            "value": option.get("value", ""),
                            "text": option.get_text(strip=True),
                        }
                    )

                field = {
                    "type": "select",
                    "name": select.get("name", ""),
                    "value": select.get("value", ""),
                    "id": select.get("id", ""),
                    "required": select.has_attr("required"),
                    "options": options,
                }
                if field["name"] or field["id"]:
                    form_data["fields"].append(field)

            forms.append(form_data)

        return forms

    def print_forms(self, forms: List[Dict]):
        """Print form information (secrets redacted)"""
        print(f"\nFound {len(forms)} form(s):")
        print("=" * 60)

        for form in forms:
            print(f"\nForm #{form['index']}")
            print(f"  Action:  {form['action']}")
            print(f"  Method:  {form['method']}")
            print(f"  Fields:  {len(form['fields'])}")

            for field in form["fields"]:
                req = " [REQUIRED]" if field.get("required") else ""
                print(f"\n  - {field['type'].upper()}{req}")
                print(f"    Name:  {field['name'] or '(no name)'}")
                print(f"    ID:    {field['id'] or '(no id)'}")
                if field.get("value"):
                    shown = redact_value(field.get("name", ""), field["value"])
                    print(f"    Value: {shown}")
                if field.get("options"):
                    print("    Options:")
                    for opt in field["options"][:5]:
                        print(f"      - {opt['value']}: {opt['text']}")

    def submit_form(self, form: Dict, data: Dict) -> Dict:
        """Submit form with data (SSRF-checked destination)"""
        url = form["action"]
        method = form["method"]

        try:
            validate_url(url)
        except SecurityError as e:
            print(f"✗ Security: blocked form action URL: {e}")
            return {"error": f"Blocked form action: {e}"}

        form_data = {}
        for field in form["fields"]:
            field_name = field["name"]
            if not field_name:
                continue
            if field_name in data:
                form_data[field_name] = data[field_name]
            elif field.get("value"):
                form_data[field_name] = field["value"]

        try:
            if method == "POST":
                response = self.session.post(url, data=form_data, timeout=10)
            else:
                response = self.session.get(url, params=form_data, timeout=10)

            print(f"✓ Form submitted to {url}")
            print(f"  Status: {response.status_code}")
            print(f"  Method: {method}")

            return {
                "status": response.status_code,
                "url": response.url,
                "headers": {
                    k: v
                    for k, v in response.headers.items()
                    if k.lower() not in ("set-cookie", "authorization")
                },
                "content_length": len(response.content),
            }

        except self.requests.exceptions.RequestException as e:
            print(f"✗ Error submitting form: {e}")
            return {"error": str(e)}

    def automate_form(self, url: str, form_index: int, data: Dict) -> Dict:
        """Complete form automation workflow"""
        html = self.fetch(url)
        if not html:
            return {"error": "Failed to fetch page"}

        forms = self.extract_forms(html, url)
        if not forms:
            return {"error": "No forms found on page"}

        if form_index < 0 or form_index >= len(forms):
            return {
                "error": f"Form index {form_index} out of range "
                f"(found {len(forms)} forms)"
            }

        return self.submit_form(forms[form_index], data)

    def login(
        self,
        login_url: str,
        username: str,
        password: str,
        username_field: str = "username",
        password_field: str = "password",
    ) -> Dict:
        """Automate login form (uses actual field names from the page)."""
        html = self.fetch(login_url)
        if not html:
            return {"error": "Failed to fetch login page"}

        forms = self.extract_forms(html, login_url)
        if not forms:
            return {"error": "No login form found"}

        # Prefer the first form that looks like a login form
        target_form = None
        resolved_user_field = None
        resolved_pass_field = None

        for form in forms:
            user_name = None
            pass_name = None
            for field in form["fields"]:
                name = field.get("name") or ""
                ftype = (field.get("type") or "").lower()
                if name == username_field or (
                    "user" in name.lower() or "email" in name.lower() or "login" in name.lower()
                ):
                    if ftype != "password":
                        user_name = name
                if name == password_field or ftype == "password" or "pass" in name.lower():
                    pass_name = name
            if user_name and pass_name:
                target_form = form
                resolved_user_field = user_name
                resolved_pass_field = pass_name
                break

        if not target_form or not resolved_user_field or not resolved_pass_field:
            return {"error": "Could not find username/password fields"}

        login_data = {
            resolved_user_field: username,
            resolved_pass_field: password,
        }
        # Include other default/hidden fields (e.g. CSRF) without overriding creds
        for field in target_form["fields"]:
            name = field.get("name")
            if name and name not in login_data and field.get("value"):
                login_data[name] = field["value"]

        return self.submit_form(target_form, login_data)


def main():
    """Main entry point for form automation"""
    if len(sys.argv) < 2:
        print("Usage: python form_automation.py <url> [options]")
        print("\nOptions:")
        print("  --list-forms           List all forms on page")
        print("  --submit <index>       Submit form by index")
        print("  --data <json>          Form data as JSON string")
        print("  --data-file <file>     Form data from JSON file")
        print("  --login                Automate login")
        print("  --username <user>      Username for login")
        print("  --password <pass>      Password for login (prefer env WEBTOOLS_PASSWORD)")
        sys.exit(1)

    url = sys.argv[1]
    automation = FormAutomation()

    list_forms = "--list-forms" in sys.argv
    submit_index = None
    form_data = None
    login_mode = "--login" in sys.argv
    username = None
    password = None

    if "--submit" in sys.argv:
        submit_idx = sys.argv.index("--submit") + 1
        if submit_idx < len(sys.argv):
            try:
                submit_index = int(sys.argv[submit_idx])
            except ValueError:
                print("✗ Error: --submit index must be an integer")
                sys.exit(1)

    if "--data" in sys.argv:
        data_idx = sys.argv.index("--data") + 1
        if data_idx < len(sys.argv):
            try:
                form_data = json.loads(sys.argv[data_idx])
            except json.JSONDecodeError as e:
                print(f"✗ Error: invalid JSON for --data: {e}")
                sys.exit(1)

    if "--data-file" in sys.argv:
        file_idx = sys.argv.index("--data-file") + 1
        if file_idx < len(sys.argv):
            try:
                form_data = safe_read_json(sys.argv[file_idx])
            except (SecurityError, OSError, json.JSONDecodeError) as e:
                print(f"✗ Error loading data file: {e}")
                sys.exit(1)

    if "--username" in sys.argv:
        user_idx = sys.argv.index("--username") + 1
        if user_idx < len(sys.argv):
            username = sys.argv[user_idx]

    # Prefer environment variable over argv to avoid process-list leaks
    import os

    if "--password" in sys.argv:
        pass_idx = sys.argv.index("--password") + 1
        if pass_idx < len(sys.argv):
            password = sys.argv[pass_idx]
            print(
                "⚠ Warning: passwords on the command line are visible in "
                "process lists. Prefer: export WEBTOOLS_PASSWORD=..."
            )
    if not password:
        password = os.environ.get("WEBTOOLS_PASSWORD")

    if list_forms:
        html = automation.fetch(url)
        if html:
            forms = automation.extract_forms(html, url)
            automation.print_forms(forms)

    elif login_mode:
        if not username or not password:
            print(
                "✗ Error: --username and --password (or WEBTOOLS_PASSWORD) "
                "required for login"
            )
            sys.exit(1)
        result = automation.login(url, username, password)
        # Never echo password back
        print("\nLogin Result:")
        print(json.dumps(result, indent=2))

    elif submit_index is not None:
        if not form_data:
            print("✗ Error: --data or --data-file required for form submission")
            sys.exit(1)
        result = automation.automate_form(url, submit_index, form_data)
        print("\nSubmission Result:")
        print(json.dumps(result, indent=2))

    else:
        print("Please specify an action: --list-forms, --submit, or --login")


if __name__ == "__main__":
    main()
