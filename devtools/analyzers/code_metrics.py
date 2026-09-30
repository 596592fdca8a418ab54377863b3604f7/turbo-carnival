#!/usr/bin/env python3
"""
Code Metrics Analyzer - Analyze code files for metrics and statistics
"""

import ast
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List

try:
    from utils.security import (
        SecurityError,
        assert_readable_directory,
        assert_readable_file,
        assert_safe_write_path,
        parse_positive_int,
        resolve_path,
    )
except ImportError:
    from pathlib import Path as _P
    sys.path.insert(0, str(_P(__file__).resolve().parents[1]))
    from utils.security import (
        SecurityError,
        assert_readable_directory,
        assert_readable_file,
        assert_safe_write_path,
        parse_positive_int,
        resolve_path,
    )


class CodeMetricsAnalyzer:
    """Analyze code files and extract metrics"""

    # Skip noisy / sensitive trees by default
    SKIP_DIRS = {'.git', '.hg', '.svn', '__pycache__', 'node_modules', '.venv', 'venv', '.tox'}

    def __init__(self, path: str):
        self.path = Path(path)
        self.metrics: Dict = {}

    def analyze_file(self, file_path: Path) -> Dict:
        """Analyze a single Python file"""
        metrics = {
            'file': str(file_path),
            'lines': 0,
            'code_lines': 0,
            'comment_lines': 0,
            'blank_lines': 0,
            'functions': 0,
            'classes': 0,
            'imports': 0,
            'docstrings': 0
        }

        try:
            safe_path = assert_readable_file(file_path)
            with open(safe_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                lines = content.splitlines() or ([content] if content else [])

            metrics['lines'] = len(lines)

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    metrics['blank_lines'] += 1
                elif stripped.startswith('#'):
                    metrics['comment_lines'] += 1
                else:
                    metrics['code_lines'] += 1

            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        metrics['functions'] += 1
                    elif isinstance(node, ast.ClassDef):
                        metrics['classes'] += 1
                    elif isinstance(node, (ast.Import, ast.ImportFrom)):
                        metrics['imports'] += 1
                    elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                        if isinstance(node.value.value, str):
                            metrics['docstrings'] += 1
            except SyntaxError:
                pass
            except RecursionError:
                print(f"✗ Skipping deeply nested AST in {file_path}")

        except SecurityError as e:
            print(f"✗ Security analyzing {file_path}: {e}")
        except OSError as e:
            print(f"✗ Error analyzing {file_path}: {e}")

        return metrics

    def analyze_directory(self) -> Dict:
        """Analyze all Python files in a directory"""
        all_metrics = []
        total_metrics = {
            'total_files': 0,
            'total_lines': 0,
            'total_code_lines': 0,
            'total_comment_lines': 0,
            'total_blank_lines': 0,
            'total_functions': 0,
            'total_classes': 0,
            'file_extensions': Counter()
        }

        try:
            self.path = resolve_path(self.path)
        except SecurityError as e:
            print(f"✗ Security: {e}")
            self.metrics = {'files': [], 'totals': total_metrics}
            return self.metrics

        if self.path.is_file():
            if self.path.suffix == '.py':
                metrics = self.analyze_file(self.path)
                all_metrics.append(metrics)
                total_metrics['total_files'] = 1
        elif self.path.is_dir():
            try:
                assert_readable_directory(self.path)
            except SecurityError as e:
                print(f"✗ Security: {e}")
                self.metrics = {'files': [], 'totals': total_metrics}
                return self.metrics

            for file_path in self.path.rglob('*.py'):
                # Skip VCS / dependency trees and symlink escapes
                if any(part in self.SKIP_DIRS for part in file_path.parts):
                    continue
                try:
                    if file_path.is_symlink():
                        continue
                    # Ensure file remains under the scan root
                    file_path.resolve(strict=False).relative_to(self.path.resolve(strict=False))
                except (ValueError, OSError):
                    continue
                metrics = self.analyze_file(file_path)
                all_metrics.append(metrics)
                total_metrics['total_files'] += 1
        else:
            print(f"✗ Error: Path does not exist: {self.path}")

        for metrics in all_metrics:
            total_metrics['total_lines'] += metrics['lines']
            total_metrics['total_code_lines'] += metrics['code_lines']
            total_metrics['total_comment_lines'] += metrics['comment_lines']
            total_metrics['total_blank_lines'] += metrics['blank_lines']
            total_metrics['total_functions'] += metrics['functions']
            total_metrics['total_classes'] += metrics['classes']

        self.metrics = {
            'files': all_metrics,
            'totals': total_metrics
        }

        return self.metrics

    def print_summary(self):
        """Print analysis summary"""
        if not self.metrics:
            print("No metrics to display")
            return

        totals = self.metrics['totals']
        print("\n" + "=" * 60)
        print("CODE METRICS SUMMARY")
        print("=" * 60)
        print(f"Path:              {self.path}")
        print(f"Total Files:       {totals['total_files']}")
        print(f"Total Lines:       {totals['total_lines']}")
        print(f"Code Lines:        {totals['total_code_lines']}")
        print(f"Comment Lines:     {totals['total_comment_lines']}")
        print(f"Blank Lines:       {totals['total_blank_lines']}")
        print(f"Total Functions:   {totals['total_functions']}")
        print(f"Total Classes:     {totals['total_classes']}")
        if totals['total_files'] > 0:
            print(f"Avg Lines/File:    {totals['total_lines'] // totals['total_files']}")
            print(f"Avg Functions/File: {totals['total_functions'] / totals['total_files']:.1f}")
        print("=" * 60)

    def print_file_details(self, limit: int = 20):
        """Print detailed metrics for each file"""
        if not self.metrics or not self.metrics['files']:
            return

        print("\nFile Details:")
        print("-" * 80)
        print(f"{'File':<40} {'Lines':>8} {'Code':>8} {'Funcs':>8} {'Classes':>8}")
        print("-" * 80)

        for metrics in self.metrics['files'][:limit]:
            file_name = Path(metrics['file']).name
            print(f"{file_name:<40} {metrics['lines']:>8} {metrics['code_lines']:>8} "
                  f"{metrics['functions']:>8} {metrics['classes']:>8}")

        if len(self.metrics['files']) > limit:
            print(f"... and {len(self.metrics['files']) - limit} more files")

    def find_large_files(self, threshold: int = 500) -> List[Dict]:
        """Find files with more lines than threshold"""
        if not self.metrics:
            return []
        return [m for m in self.metrics['files'] if m['lines'] > threshold]

    def find_complex_files(self, function_threshold: int = 10) -> List[Dict]:
        """Find files with many functions (potential complexity)"""
        if not self.metrics:
            return []
        return [m for m in self.metrics['files'] if m['functions'] > function_threshold]

    def generate_report(self, output_file: str = None):
        """Generate detailed report"""
        if not self.metrics:
            return

        report_lines = []
        report_lines.append("Code Metrics Report")
        report_lines.append("=" * 60)
        report_lines.append(f"Path: {self.path}")
        report_lines.append(f"Total Files: {self.metrics['totals']['total_files']}")
        report_lines.append(f"Total Lines: {self.metrics['totals']['total_lines']}")
        report_lines.append(f"Code Lines: {self.metrics['totals']['total_code_lines']}")
        report_lines.append(f"Comment Lines: {self.metrics['totals']['total_comment_lines']}")
        report_lines.append(f"Blank Lines: {self.metrics['totals']['total_blank_lines']}")
        report_lines.append(f"Total Functions: {self.metrics['totals']['total_functions']}")
        report_lines.append(f"Total Classes: {self.metrics['totals']['total_classes']}")

        large_files = self.find_large_files()
        if large_files:
            report_lines.append("\nLarge Files (>500 lines):")
            for metrics in large_files:
                report_lines.append(f"  {Path(metrics['file']).name}: {metrics['lines']} lines")

        complex_files = self.find_complex_files()
        if complex_files:
            report_lines.append("\nComplex Files (>10 functions):")
            for metrics in complex_files:
                report_lines.append(
                    f"  {Path(metrics['file']).name}: {metrics['functions']} functions"
                )

        report_text = "\n".join(report_lines)

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
    """Main entry point for code metrics analyzer"""
    if len(sys.argv) < 2:
        print("Usage: python code_metrics.py <path> [options]")
        print("\nOptions:")
        print("  --details          Show detailed file metrics")
        print("  --large <N>        Find files with >N lines (default: 500)")
        print("  --complex <N>      Find files with >N functions (default: 10)")
        print("  --report <file>    Save report to file")
        sys.exit(1)

    path = sys.argv[1]
    if path.startswith('-'):
        print("✗ Error: Please specify a path before options")
        sys.exit(1)

    analyzer = CodeMetricsAnalyzer(path)
    analyzer.analyze_directory()
    analyzer.print_summary()

    if '--details' in sys.argv:
        analyzer.print_file_details()

    try:
        if '--large' in sys.argv:
            large_idx = sys.argv.index('--large') + 1
            threshold = (
                parse_positive_int(sys.argv[large_idx], name='--large', allow_zero=False)
                if large_idx < len(sys.argv) and not sys.argv[large_idx].startswith('-')
                else 500
            )
            large_files = analyzer.find_large_files(threshold)
            print(f"\nLarge Files (>{threshold} lines): {len(large_files)}")
            for metrics in large_files:
                print(f"  {Path(metrics['file']).name}: {metrics['lines']} lines")

        if '--complex' in sys.argv:
            complex_idx = sys.argv.index('--complex') + 1
            threshold = (
                parse_positive_int(sys.argv[complex_idx], name='--complex', allow_zero=False)
                if complex_idx < len(sys.argv) and not sys.argv[complex_idx].startswith('-')
                else 10
            )
            complex_files = analyzer.find_complex_files(threshold)
            print(f"\nComplex Files (>{threshold} functions): {len(complex_files)}")
            for metrics in complex_files:
                print(f"  {Path(metrics['file']).name}: {metrics['functions']} functions")
    except SecurityError as e:
        print(f"✗ Security: {e}")
        sys.exit(1)

    if '--report' in sys.argv:
        report_idx = sys.argv.index('--report') + 1
        if report_idx < len(sys.argv):
            analyzer.generate_report(sys.argv[report_idx])


if __name__ == "__main__":
    main()
