#!/usr/bin/env python3
"""
Data Transformer - Convert between JSON, CSV, and other formats
"""

import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

try:
    from utils.security import (
        SecurityError,
        assert_readable_file,
        assert_safe_write_path,
        escape_csv_formula,
    )
except ImportError:
    from pathlib import Path as _P
    sys.path.insert(0, str(_P(__file__).resolve().parents[1]))
    from utils.security import (
        SecurityError,
        assert_readable_file,
        assert_safe_write_path,
        escape_csv_formula,
    )


class DataTransformer:
    """Transform data between different formats"""

    def __init__(self, input_file: str):
        self.input_file = Path(input_file)
        self.data: Any = None

    def load_json(self) -> bool:
        """Load JSON file with size / path checks"""
        try:
            safe_path = assert_readable_file(self.input_file)
            self.input_file = safe_path
            with open(safe_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            print(f"✓ Loaded JSON from {self.input_file}")
            return True
        except SecurityError as e:
            print(f"✗ Security: {e}")
            return False
        except FileNotFoundError:
            print(f"✗ Error: File '{self.input_file}' not found")
            return False
        except json.JSONDecodeError as e:
            print(f"✗ Error parsing JSON: {e}")
            return False
        except OSError as e:
            print(f"✗ Error reading file: {e}")
            return False

    def load_csv(self) -> bool:
        """Load CSV file with size / path checks"""
        try:
            safe_path = assert_readable_file(self.input_file)
            self.input_file = safe_path
            with open(safe_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                self.data = list(reader)
            print(f"✓ Loaded CSV from {self.input_file} ({len(self.data)} rows)")
            return True
        except SecurityError as e:
            print(f"✗ Security: {e}")
            return False
        except FileNotFoundError:
            print(f"✗ Error: File '{self.input_file}' not found")
            return False
        except OSError as e:
            print(f"✗ Error reading CSV: {e}")
            return False

    def save_json(self, output_file: str, indent: int = 2) -> bool:
        """Save data as JSON"""
        try:
            safe_out = assert_safe_write_path(output_file)
            with open(safe_out, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=indent, ensure_ascii=False)
            print(f"✓ Saved JSON to {safe_out}")
            return True
        except SecurityError as e:
            print(f"✗ Security: {e}")
            return False
        except OSError as e:
            print(f"✗ Error saving JSON: {e}")
            return False

    def save_csv(self, output_file: str) -> bool:
        """Save data as CSV with formula-injection escaping"""
        try:
            if not isinstance(self.data, list):
                print("✗ Error: Data must be a list of dictionaries for CSV export")
                return False

            if not self.data:
                print("✗ Error: No data to save")
                return False

            if not all(isinstance(row, dict) for row in self.data):
                print("✗ Error: CSV export requires a list of dictionaries")
                return False

            # Union of keys across rows so later rows don't lose columns
            fieldnames = list(dict.fromkeys(
                key for row in self.data for key in row.keys()
            ))
            safe_out = assert_safe_write_path(output_file)
            with open(safe_out, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                for row in self.data:
                    safe_row = {k: escape_csv_formula(row.get(k)) for k in fieldnames}
                    writer.writerow(safe_row)
            print(f"✓ Saved CSV to {safe_out} ({len(self.data)} rows)")
            return True
        except SecurityError as e:
            print(f"✗ Security: {e}")
            return False
        except OSError as e:
            print(f"✗ Error saving CSV: {e}")
            return False

    def print_data(self, limit: int = 10):
        """Print data preview"""
        if isinstance(self.data, list):
            print(f"\nData preview ({len(self.data)} items):")
            print("-" * 50)
            for item in self.data[:limit]:
                print(json.dumps(item, indent=2, ensure_ascii=False))
            if len(self.data) > limit:
                print(f"... and {len(self.data) - limit} more items")
        elif isinstance(self.data, dict):
            print("\nData preview:")
            print("-" * 50)
            print(json.dumps(self.data, indent=2, ensure_ascii=False))
        else:
            print(f"\nData: {self.data}")

    def filter_data(self, key: str, value: Any) -> List:
        """Filter data by key-value pair"""
        if not isinstance(self.data, list):
            print("✗ Error: Data must be a list for filtering")
            return []

        filtered = [
            item for item in self.data
            if isinstance(item, dict) and str(item.get(key)) == str(value)
        ]
        print(f"✓ Filtered to {len(filtered)} items where {key}={value}")
        return filtered

    def transform_keys(self, mapping: Dict[str, str]) -> List:
        """Rename keys; preserve unmapped keys"""
        if not isinstance(self.data, list):
            print("✗ Error: Data must be a list for key transformation")
            return []

        transformed = []
        for item in self.data:
            if not isinstance(item, dict):
                continue
            new_item = {}
            for old_key, value in item.items():
                new_key = mapping.get(old_key, old_key)
                new_item[new_key] = value
            transformed.append(new_item)

        self.data = transformed
        print(f"✓ Transformed keys using mapping: {mapping}")
        return transformed

    def extract_fields(self, fields: List[str]) -> List:
        """Extract only specific fields from data"""
        if not isinstance(self.data, list):
            print("✗ Error: Data must be a list for field extraction")
            return []

        extracted = []
        for item in self.data:
            if not isinstance(item, dict):
                continue
            new_item = {field: item.get(field) for field in fields if field in item}
            extracted.append(new_item)

        self.data = extracted
        print(f"✓ Extracted fields: {fields}")
        return extracted


def main():
    """Main entry point for data transformer"""
    if len(sys.argv) < 3:
        print("Usage: python data_transformer.py <input_file> <output_file> [options]")
        print("\nOptions:")
        print("  --json-to-csv      Convert JSON to CSV")
        print("  --csv-to-json      Convert CSV to JSON")
        print("  --filter <key> <value>   Filter data")
        print("  --fields <field1,field2>  Extract specific fields")
        print("  --rename <old:new>       Rename keys (can use multiple)")
        print("  --preview          Show data preview")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    if input_file.startswith('-') or output_file.startswith('-'):
        print("✗ Error: Please specify input and output files before options")
        sys.exit(1)

    transformer = DataTransformer(input_file)

    if input_file.endswith('.json'):
        if not transformer.load_json():
            sys.exit(1)
    elif input_file.endswith('.csv'):
        if not transformer.load_csv():
            sys.exit(1)
    else:
        print("✗ Error: Unsupported input format. Use .json or .csv")
        sys.exit(1)

    if '--filter' in sys.argv:
        filter_idx = sys.argv.index('--filter') + 1
        if filter_idx + 1 < len(sys.argv):
            key = sys.argv[filter_idx]
            value = sys.argv[filter_idx + 1]
            transformer.data = transformer.filter_data(key, value)

    if '--fields' in sys.argv:
        fields_idx = sys.argv.index('--fields') + 1
        if fields_idx < len(sys.argv):
            fields = [f.strip() for f in sys.argv[fields_idx].split(',') if f.strip()]
            transformer.extract_fields(fields)

    if '--rename' in sys.argv:
        mapping = {}
        for i, arg in enumerate(sys.argv):
            if arg == '--rename' and i + 1 < len(sys.argv):
                rename_spec = sys.argv[i + 1]
                if ':' in rename_spec:
                    old_key, new_key = rename_spec.split(':', 1)
                    if old_key and new_key:
                        mapping[old_key] = new_key
        if mapping:
            transformer.transform_keys(mapping)

    if '--preview' in sys.argv:
        transformer.print_data()

    if '--json-to-csv' in sys.argv:
        ok = transformer.save_csv(output_file)
    elif '--csv-to-json' in sys.argv:
        ok = transformer.save_json(output_file)
    elif output_file.endswith('.json'):
        ok = transformer.save_json(output_file)
    elif output_file.endswith('.csv'):
        ok = transformer.save_csv(output_file)
    else:
        print("✗ Error: Unsupported output format. Use .json or .csv")
        sys.exit(1)

    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
