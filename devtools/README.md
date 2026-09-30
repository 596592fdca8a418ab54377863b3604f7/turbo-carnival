# DevTools CLI - Terminal Automation for Developers

A collection of powerful terminal-based automation tools for developers, built with Python. These tools help you analyze logs, transform data, measure code metrics, and organize files - all from the command line.

## Features

- **Log Analyzer**: Analyze log files for errors, warnings, and patterns
- **Data Transformer**: Convert between JSON, CSV, and other formats
- **Code Metrics**: Analyze code complexity and statistics
- **File Organizer**: Search, organize, and manage files efficiently

## Installation

No installation required! These tools use only Python's standard library.

### Prerequisites
- Python 3.6 or higher

### Setup
```bash
# Clone or download the devtools directory
cd devtools

# Make the CLI executable (optional)
chmod +x cli.py
```

## Usage

### Main CLI Entry Point

```bash
python cli.py <command> [arguments]
```

### Available Commands

#### 1. Log Analyzer
Analyze log files for errors, warnings, and patterns.

```bash
# Basic analysis
python cli.py log-analyzer sample.log

# Show only errors
python cli.py log-analyzer app.log --errors-only

# Search for custom pattern
python cli.py log-analyzer app.log --pattern "database"

# Generate report
python cli.py log-analyzer app.log --report report.txt
```

#### 2. Code Metrics
Analyze code complexity and statistics for files or directories.

```bash
# Analyze directory
python cli.py code-metrics ./src

# Show detailed file metrics
python cli.py code-metrics ./src --details

# Find large files
python cli.py code-metrics ./src --large 500

# Find complex files
python cli.py code-metrics ./src --complex 10

# Generate report
python cli.py code-metrics ./src --report metrics.txt
```

#### 3. Data Transformer
Convert data between JSON, CSV, and other formats.

```bash
# Convert JSON to CSV
python cli.py data-transform data.json output.csv --json-to-csv

# Convert CSV to JSON
python cli.py data-transform data.csv output.json --csv-to-json

# Filter data
python cli.py data-transform data.json filtered.json --filter department Engineering

# Extract specific fields
python cli.py data-transform data.json output.json --fields name,email,department

# Preview data
python cli.py data-transform data.json output.json --preview
```

#### 4. File Organizer
Search, organize, and manage files.

```bash
# Search by extension
python cli.py file-organizer ./project --ext .py

# Search by name pattern
python cli.py file-organizer ./project --name "test"

# Search by size range
python cli.py file-organizer ./project --size 1000 10000

# Search recently modified files
python cli.py file-organizer ./project --days 7

# Organize files by extension (dry run)
python cli.py file-organizer ./project --organize ./organized

# Execute organization (not dry run)
python cli.py file-organizer ./project --organize ./organized --execute

# Find duplicate files
python cli.py file-organizer ./project --duplicates

# Find empty directories
python cli.py file-organizer ./project --clean-empty
```

## Individual Tool Usage

You can also run each tool directly:

```bash
# Log Analyzer
python analyzers/log_analyzer.py <log_file> [options]

# Code Metrics
python analyzers/code_metrics.py <path> [options]

# Data Transformer
python transformers/data_transformer.py <input> <output> [options]

# File Organizer
python utils/file_organizer.py <directory> [options]
```

## Project Structure

```
devtools/
├── cli.py                      # Main CLI entry point
├── analyzers/
│   ├── log_analyzer.py        # Log file analysis
│   └── code_metrics.py        # Code metrics analysis
├── transformers/
│   └── data_transformer.py    # Data transformation
├── utils/
│   └── file_organizer.py      # File organization
├── sample.log                 # Sample log file for testing
├── sample_data.json           # Sample data for testing
└── README.md                  # This file
```

## Examples

### Analyze Application Logs
```bash
python cli.py log-analyzer /var/log/app.log --errors-only --report errors.txt
```

### Transform API Response Data
```bash
python cli.py data-transform api_response.json users.csv --json-to-csv --fields id,name,email
```

### Analyze Project Code Quality
```bash
python cli.py code-metrics ./my-project --details --large 1000 --complex 15
```

### Clean Up Project Files
```bash
python cli.py file-organizer ./my-project --ext .tmp --days 30
```

## Benefits of Terminal Automation

- **Faster**: No GUI overhead, direct command execution
- **Scriptable**: Easy to integrate into scripts and CI/CD pipelines
- **Efficient**: Lower resource usage than web/mobile apps
- **Portable**: Works on any system with Python
- **Automatable**: Can be scheduled with cron or task schedulers
- **Flexible**: Easy to customize and extend

## Future Enhancements

Potential additions:
- Git repository analyzer
- Dependency checker
- Test coverage reporter
- Performance profiler
- Database query analyzer
- API testing tool
- Deployment automation

## Contributing

Feel free to extend these tools for your specific needs. Each tool is modular and can be enhanced independently.

## License

Free to use and modify for any purpose.
