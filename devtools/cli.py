#!/usr/bin/env python3
"""
DevTools CLI - Main entry point for developer automation tools
"""

import sys
from pathlib import Path

# Add package root for imports when run as a script
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def print_banner():
    """Print CLI banner"""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                    DevTools CLI v1.0.1                         ║
║              Terminal Automation for Developers                ║
╚═══════════════════════════════════════════════════════════════╝
    """)


def print_help():
    """Print help information"""
    print("""
DevTools CLI - Terminal Automation Tools

Usage: python cli.py <command> [arguments]

Commands:
  log-analyzer <file>          Analyze log files for errors and warnings
  code-metrics <path>          Analyze code metrics for files/directories
  data-transform <input> <output>  Transform data between JSON/CSV
  file-organizer <directory>   Organize and search files

Options for log-analyzer:
  --errors-only                Show only errors
  --warnings-only              Show only warnings
  --pattern <regex>            Search for custom pattern
  --report <file>              Save report to file

Options for code-metrics:
  --details                    Show detailed file metrics
  --large <N>                  Find files with >N lines
  --complex <N>                Find files with >N functions
  --report <file>              Save report to file

Options for data-transform:
  --json-to-csv                Convert JSON to CSV
  --csv-to-json                Convert CSV to JSON
  --filter <key> <value>       Filter data
  --fields <field1,field2>     Extract specific fields
  --rename <old:new>           Rename keys
  --preview                    Show data preview

Options for file-organizer:
  --name <pattern>             Search by name pattern
  --ext <extension>            Search by extension
  --size <min> <max>           Search by size range
  --days <N>                   Search files modified in last N days
  --organize <dir>             Organize files by extension
  --duplicates                 Find duplicate files
  --clean-empty                Find empty directories
  --execute                    Execute operations (not dry run)
  --limit <N>                  Limit results display

Examples:
  python cli.py log-analyzer app.log
  python cli.py code-metrics ./src --details
  python cli.py data-transform data.json output.csv --json-to-csv
  python cli.py file-organizer ./project --ext .py

For more help on a specific command:
  python cli.py <command> --help
    """)


def _dispatch(module_argv_name: str, args, runner):
    """Run a subcommand without permanently corrupting process argv."""
    original = sys.argv[:]
    try:
        sys.argv = [module_argv_name] + list(args)
        runner()
    finally:
        sys.argv = original


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print_banner()
        print_help()
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    if command in ('help', '--help', '-h'):
        print_banner()
        print_help()
        return

    print_banner()

    if command == 'log-analyzer':
        if not args or args[0].startswith('-'):
            print("Error: Please specify a log file")
            sys.exit(1)
        from analyzers.log_analyzer import main as log_main
        _dispatch('log_analyzer.py', args, log_main)

    elif command == 'code-metrics':
        if not args or args[0].startswith('-'):
            print("Error: Please specify a path to analyze")
            sys.exit(1)
        from analyzers.code_metrics import main as metrics_main
        _dispatch('code_metrics.py', args, metrics_main)

    elif command == 'data-transform':
        if len(args) < 2 or args[0].startswith('-') or args[1].startswith('-'):
            print("Error: Please specify input and output files")
            sys.exit(1)
        from transformers.data_transformer import main as transform_main
        _dispatch('data_transformer.py', args, transform_main)

    elif command == 'file-organizer':
        if not args or args[0].startswith('-'):
            print("Error: Please specify a directory")
            sys.exit(1)
        from utils.file_organizer import main as organize_main
        _dispatch('file_organizer.py', args, organize_main)

    else:
        # Avoid reflecting untrusted input unchecked into terminals that parse escapes
        safe_cmd = ''.join(ch for ch in command if ch.isprintable())[:64]
        print(f"Error: Unknown command '{safe_cmd}'")
        print("\nAvailable commands:")
        print("  log-analyzer")
        print("  code-metrics")
        print("  data-transform")
        print("  file-organizer")
        print("  help")
        sys.exit(1)


if __name__ == "__main__":
    main()
