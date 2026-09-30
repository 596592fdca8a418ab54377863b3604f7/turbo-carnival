#!/usr/bin/env python3
"""
Log File Analyzer - Analyze log files for errors, warnings, and patterns
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Support both `python cli.py` and direct module execution
try:
    from utils.security import (
        SecurityError,
        assert_readable_file,
        assert_safe_write_path,
        regex_search_with_timeout,
        safe_compile_regex,
    )
except ImportError:
    from pathlib import Path as _P
    sys.path.insert(0, str(_P(__file__).resolve().parents[1]))
    from utils.security import (
        SecurityError,
        assert_readable_file,
        assert_safe_write_path,
        regex_search_with_timeout,
        safe_compile_regex,
    )


class LogAnalyzer:
    """Analyze log files and extract useful information"""

    def __init__(self, log_file: str):
        self.log_file = Path(log_file)
        self.lines: List[str] = []
        self.errors: List[Tuple[int, str]] = []
        self.warnings: List[Tuple[int, str]] = []
        self.info: List[Tuple[int, str]] = []

    def load_log(self) -> bool:
        """Load log file into memory with size and path checks"""
        try:
            safe_path = assert_readable_file(self.log_file)
            self.log_file = safe_path
            with open(safe_path, 'r', encoding='utf-8', errors='replace') as f:
                self.lines = f.readlines()
            print(f"✓ Loaded {len(self.lines)} lines from {self.log_file}")
            return True
        except SecurityError as e:
            print(f"✗ Security: {e}")
            return False
        except FileNotFoundError:
            print(f"✗ Error: File '{self.log_file}' not found")
            return False
        except OSError as e:
            print(f"✗ Error reading file: {e}")
            return False

    def analyze(self):
        """Analyze log lines for errors, warnings, and info"""
        error_pattern = re.compile(r'(error|exception|failed|critical)', re.IGNORECASE)
        warning_pattern = re.compile(r'(warning|warn)', re.IGNORECASE)
        info_pattern = re.compile(r'(info|debug)', re.IGNORECASE)

        for idx, line in enumerate(self.lines, 1):
            if error_pattern.search(line):
                self.errors.append((idx, line.strip()))
            elif warning_pattern.search(line):
                self.warnings.append((idx, line.strip()))
            elif info_pattern.search(line):
                self.info.append((idx, line.strip()))

    def get_summary(self) -> Dict:
        """Get analysis summary"""
        return {
            'total_lines': len(self.lines),
            'errors': len(self.errors),
            'warnings': len(self.warnings),
            'info': len(self.info),
            'error_rate': len(self.errors) / len(self.lines) * 100 if self.lines else 0
        }

    def print_summary(self):
        """Print analysis summary"""
        summary = self.get_summary()
        print("\n" + "=" * 50)
        print("LOG ANALYSIS SUMMARY")
        print("=" * 50)
        print(f"Total Lines:      {summary['total_lines']}")
        print(f"Errors:           {summary['errors']}")
        print(f"Warnings:         {summary['warnings']}")
        print(f"Info:             {summary['info']}")
        print(f"Error Rate:       {summary['error_rate']:.2f}%")
        print("=" * 50)

    def _format_line(self, line: str, max_len: int = 100) -> str:
        if len(line) <= max_len:
            return line
        return line[:max_len] + "..."

    def print_errors(self, limit: int = 10):
        """Print error lines"""
        if not self.errors:
            print("\n✓ No errors found")
            return

        print(f"\nErrors found ({len(self.errors)} total):")
        print("-" * 50)
        for line_num, line in self.errors[:limit]:
            print(f"Line {line_num}: {self._format_line(line)}")
        if len(self.errors) > limit:
            print(f"... and {len(self.errors) - limit} more errors")

    def print_warnings(self, limit: int = 10):
        """Print warning lines"""
        if not self.warnings:
            print("\n✓ No warnings found")
            return

        print(f"\nWarnings found ({len(self.warnings)} total):")
        print("-" * 50)
        for line_num, line in self.warnings[:limit]:
            print(f"Line {line_num}: {self._format_line(line)}")
        if len(self.warnings) > limit:
            print(f"... and {len(self.warnings) - limit} more warnings")

    def extract_patterns(self, pattern: str) -> List[Tuple[int, str]]:
        """Extract lines matching a custom pattern (ReDoS-hardened)"""
        compiled = safe_compile_regex(pattern, re.IGNORECASE)
        matches = []
        for idx, line in enumerate(self.lines, 1):
            if regex_search_with_timeout(compiled, line) is not None:
                matches.append((idx, line.strip()))
        return matches

    def generate_report(self, output_file: str = None):
        """Generate a detailed report"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report = []
        report.append("Log Analysis Report")
        report.append(f"Generated: {timestamp}")
        report.append(f"File: {self.log_file}")
        report.append("=" * 50)

        summary = self.get_summary()
        report.append("\nSummary:")
        report.append(f"  Total Lines: {summary['total_lines']}")
        report.append(f"  Errors: {summary['errors']}")
        report.append(f"  Warnings: {summary['warnings']}")
        report.append(f"  Info: {summary['info']}")
        report.append(f"  Error Rate: {summary['error_rate']:.2f}%")

        if self.errors:
            report.append("\nTop 10 Errors:")
            for line_num, line in self.errors[:10]:
                report.append(f"  Line {line_num}: {line}")

        if self.warnings:
            report.append("\nTop 10 Warnings:")
            for line_num, line in self.warnings[:10]:
                report.append(f"  Line {line_num}: {line}")

        report_text = "\n".join(report)

        if output_file:
            try:
                safe_out = assert_safe_write_path(output_file)
                with open(safe_out, 'w', encoding='utf-8') as f:
                    f.write(report_text)
                print(f"\n✓ Report saved to {safe_out}")
            except SecurityError as e:
                print(f"✗ Security: {e}")
            except OSError as e:
                print(f"✗ Error writing report: {e}")
        else:
            print("\n" + report_text)


def main():
    """Main entry point for log analyzer"""
    if len(sys.argv) < 2:
        print("Usage: python log_analyzer.py <log_file> [options]")
        print("\nOptions:")
        print("  --report <file>    Save report to file")
        print("  --pattern <regex>  Search for custom pattern")
        print("  --errors-only      Show only errors")
        print("  --warnings-only    Show only warnings")
        sys.exit(1)

    log_file = sys.argv[1]
    if log_file.startswith('-'):
        print("✗ Error: Please specify a log file before options")
        sys.exit(1)

    analyzer = LogAnalyzer(log_file)

    if not analyzer.load_log():
        sys.exit(1)

    analyzer.analyze()
    analyzer.print_summary()

    if '--errors-only' in sys.argv:
        analyzer.print_errors()
    elif '--warnings-only' in sys.argv:
        analyzer.print_warnings()
    else:
        analyzer.print_errors()
        analyzer.print_warnings()

    if '--pattern' in sys.argv:
        pattern_idx = sys.argv.index('--pattern') + 1
        if pattern_idx < len(sys.argv):
            pattern = sys.argv[pattern_idx]
            try:
                matches = analyzer.extract_patterns(pattern)
            except SecurityError as e:
                print(f"✗ Security: {e}")
                sys.exit(1)
            print(f"\nPattern '{pattern}' matches ({len(matches)} found):")
            for line_num, line in matches[:10]:
                display = line if len(line) <= 100 else line[:100] + "..."
                print(f"  Line {line_num}: {display}")

    if '--report' in sys.argv:
        report_idx = sys.argv.index('--report') + 1
        if report_idx < len(sys.argv):
            output_file = sys.argv[report_idx]
            analyzer.generate_report(output_file)


if __name__ == "__main__":
    main()
