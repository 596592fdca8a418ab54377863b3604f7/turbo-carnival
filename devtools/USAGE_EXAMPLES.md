# DevTools CLI - Practical Usage Examples

This document provides real-world scenarios and examples of when and how to use each tool in the DevTools CLI suite.

## Table of Contents
1. [Log Analyzer Examples](#log-analyzer-examples)
2. [Data Transformer Examples](#data-transformer-examples)
3. [Code Metrics Examples](#code-metrics-examples)
4. [File Organizer Examples](#file-organizer-examples)
5. [Integration & Automation Examples](#integration--automation-examples)

---

## Log Analyzer Examples

### Scenario 1: Debugging Production Issues

**Problem**: Your web application is crashing in production. You need to quickly identify the root cause from server logs.

**Solution**:
```bash
# Analyze today's application log
python cli.py log-analyzer /var/log/app.log --errors-only

# Search for specific error patterns
python cli.py log-analyzer /var/log/app.log --pattern "database"

# Generate a report for the team
python cli.py log-analyzer /var/log/app.log --report incident_report.txt
```

**Results**:
- Quickly identifies all errors with line numbers
- Shows error rate (35.29% in our test)
- Highlights critical issues like "System out of memory"
- Creates shareable report for team discussion

### Scenario 2: Daily Health Monitoring

**Problem**: You want to monitor system health daily and catch issues before they become critical.

**Solution**:
```bash
# Create a daily monitoring script
#!/bin/bash
DATE=$(date +%Y-%m-%d)
python cli.py log-analyzer /var/log/app.log --report "daily_reports/$DATE.txt"

# Check if error rate is above threshold
ERRORS=$(python cli.py log-analyzer /var/log/app.log --errors-only | grep "Errors:" | awk '{print $2}')
if [ $ERRORS -gt 10 ]; then
    echo "High error rate detected: $ERRORS errors" | mail -s "Alert: High Error Rate" admin@example.com
fi
```

### Scenario 3: Security Auditing

**Problem**: You need to find security-related events in logs (failed logins, unauthorized access).

**Solution**:
```bash
# Search for security-related patterns
python cli.py log-analyzer /var/log/auth.log --pattern "failed"
python cli.py log-analyzer /var/log/auth.log --pattern "unauthorized"
python cli.py log-analyzer /var/log/auth.log --pattern "intrusion"
```

### Scenario 4: Performance Analysis

**Problem**: Application is slow. You need to find performance-related warnings.

**Solution**:
```bash
# Find performance warnings
python cli.py log-analyzer /var/log/app.log --pattern "timeout"
python cli.py log-analyzer /var/log/app.log --pattern "slow"
python cli.py log-analyzer /var/log/app.log --pattern "latency"
```

---

## Data Transformer Examples

### Scenario 1: API Data Processing

**Problem**: You received a large JSON response from an API and need to convert it to CSV for Excel analysis.

**Solution**:
```bash
# Convert API response to CSV
python cli.py data-transform api_response.json data.csv --json-to-csv

# Filter only active users
python cli.py data-transform api_response.json active_users.csv \
  --json-to-csv \
  --filter status active

# Extract only relevant fields
python cli.py data-transform api_response.json minimal_data.csv \
  --json-to-csv \
  --fields id,name,email,created_at
```

**Test Results**:
- Successfully converted 5 records from JSON to CSV
- Filtered 3 Engineering department employees
- Extracted only name and email fields for privacy

### Scenario 2: Data Migration

**Problem**: You're migrating data from an old system (CSV) to a new system (JSON).

**Solution**:
```bash
# Convert CSV to JSON
python cli.py data-transform old_users.csv new_users.json --csv-to-json

# Transform field names to match new schema
python cli.py data-transform old_users.csv new_users.json \
  --csv-to-json \
  --rename "first_name:fname" \
  --rename "last_name:lname"
```

### Scenario 3: Data Cleaning

**Problem**: You have a large dataset and need to extract specific subsets for different teams.

**Solution**:
```bash
# Extract engineering team data
python cli.py data-transform all_employees.json engineering.json \
  --filter department Engineering

# Extract sales team data
python cli.py data-transform all_employees.json sales.json \
  --filter department Sales

# Create a mailing list (name and email only)
python cli.py data-transform all_employees.json mailing_list.json \
  --fields name,email
```

### Scenario 4: Report Generation

**Problem**: Generate different reports from the same dataset for different stakeholders.

**Solution**:
```bash
# Management report (summary data)
python cli.py data-transform data.json management.csv \
  --json-to-csv \
  --fields id,name,department,salary

# Technical report (detailed data)
python cli.py data-transform data.json technical.csv \
  --json-to-csv

# HR report (sensitive data)
python cli.py data-transform data.json hr.csv \
  --json-to-csv \
  --fields name,email,department,salary,hire_date
```

---

## Code Metrics Examples

### Scenario 1: Code Review Preparation

**Problem**: You're reviewing a pull request and want to understand the code complexity.

**Solution**:
```bash
# Analyze the changed files
python cli.py code-metrics ./src --details

# Find potentially complex files
python cli.py code-metrics ./src --large 500 --complex 10
```

**Test Results**:
- Found 9 Python files with 1,076 total lines
- Identified 3 large files (>200 lines)
- Found 4 complex files (>8 functions)
- Average: 119 lines per file, 5 functions per file

### Scenario 2: Technical Debt Assessment

**Problem**: You need to assess technical debt in your project to plan refactoring efforts.

**Solution**:
```bash
# Generate comprehensive report
python cli.py code-metrics ./project --report technical_debt.txt

# Find files that need attention
python cli.py code-metrics ./project --large 1000
python cli.py code-metrics ./project --complex 15
```

### Scenario 3: Project Health Monitoring

**Problem**: Track project health over time to ensure code quality doesn't degrade.

**Solution**:
```bash
# Weekly health check script
#!/bin/bash
WEEK=$(date +%Y-%W)
python cli.py code-metrics ./src --report "weekly_reports/$WEEK.txt"

# Compare with previous week
DIFF=$(diff weekly_reports/$((WEEK-1)).txt weekly_reports/$WEEK.txt)
if [ ! -z "$DIFF" ]; then
    echo "Code metrics changed this week"
fi
```

### Scenario 4: Onboarding New Developers

**Problem**: Help new developers understand the project structure and complexity.

**Solution**:
```bash
# Generate project overview
python cli.py code-metrics ./project --details

# Identify key files to start with
python cli.py code-metrics ./project --large 100  # Not too large
python cli.py code-metrics ./project --complex 5  # Reasonable complexity
```

---

## File Organizer Examples

### Scenario 1: Project Cleanup

**Problem**: Your project directory has accumulated temporary files and needs cleanup.

**Solution**:
```bash
# Find temporary files
python cli.py file-organizer ./project --name ".tmp"
python cli.py file-organizer ./project --name "temp"

# Find old files (>30 days)
python cli.py file-organizer ./project --days 30

# Find duplicate files
python cli.py file-organizer ./project --duplicates
```

**Test Results**:
- Found 2 files matching "sample" pattern
- Found 5 JSON files in the project
- Found 15 files between 100-1000 bytes
- Detected 2 sets of duplicate files

### Scenario 2: Code Organization

**Problem**: You want to organize your project files by type for better structure.

**Solution**:
```bash
# Preview organization (dry run)
python cli.py file-organizer ./project --organize ./organized

# Execute organization
python cli.py file-organizer ./project --organize ./organized --execute
```

**Test Results**:
- Would organize into: .csv/ (3 files), .json/ (5 files), .py/ (9 files)
- Safe dry-run mode before actual changes

### Scenario 3: Finding Specific File Types

**Problem**: You need to find all Python files in a large project.

**Solution**:
```bash
# Find all Python files
python cli.py file-organizer ./project --ext .py

# Find all configuration files
python cli.py file-organizer ./project --ext .yaml
python cli.py file-organizer ./project --ext .yml
python cli.py file-organizer ./project --ext .json
python cli.py file-organizer ./project --ext .toml
```

### Scenario 4: Disk Space Analysis

**Problem**: You're running out of disk space and need to find large files.

**Solution**:
```bash
# Find files larger than 10MB
python cli.py file-organizer ./project --size 10485760

# Find files between 1MB and 10MB
python cli.py file-organizer ./project --size 1048576 10485760

# Find recently modified large files
python cli.py file-organizer ./project --days 7 --size 1048576
```

---

## Integration & Automation Examples

### Scenario 1: CI/CD Pipeline Integration

**Problem**: You want to automatically check code quality in your CI/CD pipeline.

**Solution** (GitHub Actions example):
```yaml
name: Code Quality Check
on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Check code metrics
        run: |
          cd devtools
          python cli.py code-metrics ../src --large 1000 --complex 15
      - name: Check for temporary files
        run: |
          cd devtools
          python cli.py file-organizer ../src --name ".tmp"
```

### Scenario 2: Automated Daily Reports

**Problem**: You want daily automated reports sent to your team.

**Solution** (cron job):
```bash
# Add to crontab (runs daily at 8 AM)
0 8 * * * /path/to/devtools/daily_report.sh
```

**daily_report.sh**:
```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d)
cd /path/to/devtools

# Log analysis
python cli.py log-analyzer /var/log/app.log --report "reports/logs_$DATE.txt"

# Code metrics
python cli.py code-metrics /path/to/project --report "reports/metrics_$DATE.txt"

# Send email
echo "Daily reports attached" | mail -s "Daily Report $DATE" \
  -a reports/logs_$DATE.txt \
  -a reports/metrics_$DATE.txt \
  team@example.com
```

### Scenario 3: Pre-commit Hook

**Problem**: You want to prevent large, complex files from being committed.

**Solution** (.git/hooks/pre-commit):
```bash
#!/bin/bash
cd devtools

# Check for files that are too large
LARGE_FILES=$(python cli.py code-metrics ../src --large 500 | grep "Large Files" -A 10)
if [ ! -z "$LARGE_FILES" ]; then
    echo "Warning: Large files detected:"
    echo "$LARGE_FILES"
    echo "Please refactor before committing."
    exit 1
fi

# Check for temporary files
TEMP_FILES=$(python cli.py file-organizer ../src --name ".tmp" | grep "Results" -A 20)
if [ ! -z "$TEMP_FILES" ]; then
    echo "Error: Temporary files found:"
    echo "$TEMP_FILES"
    echo "Please remove temporary files before committing."
    exit 1
fi
```

### Scenario 4: Data Pipeline Automation

**Problem**: You need to automatically process and transform data daily.

**Solution** (automated pipeline):
```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d)
cd /path/to/devtools

# Step 1: Download data (example)
curl -o raw_data.json https://api.example.com/data

# Step 2: Transform to CSV
python cli.py data-transform raw_data.json daily_$DATE.csv --json-to-csv

# Step 3: Filter for active records
python cli.py data-transform raw_data.json active_$DATE.csv \
  --json-to-csv \
  --filter status active

# Step 4: Extract specific fields for reports
python cli.py data-transform raw_data.json report_$DATE.csv \
  --json-to-csv \
  --fields id,name,email,status

# Step 5: Upload to storage (example)
aws s3 cp daily_$DATE.csv s3://bucket/daily/

# Step 6: Clean up
rm raw_data.json
```

---

## Quick Reference Commands

### Log Analyzer
```bash
# Basic analysis
python cli.py log-analyzer <logfile>

# Errors only
python cli.py log-analyzer <logfile> --errors-only

# Pattern search
python cli.py log-analyzer <logfile> --pattern "<regex>"

# Generate report
python cli.py log-analyzer <logfile> --report <output_file>
```

### Data Transformer
```bash
# JSON to CSV
python cli.py data-transform <input.json> <output.csv> --json-to-csv

# CSV to JSON
python cli.py data-transform <input.csv> <output.json> --csv-to-json

# Filter data
python cli.py data-transform <input> <output> --filter <key> <value>

# Extract fields
python cli.py data-transform <input> <output> --fields <field1,field2>

# Preview data
python cli.py data-transform <input> <output> --preview
```

### Code Metrics
```bash
# Basic analysis
python cli.py code-metrics <path>

# Detailed view
python cli.py code-metrics <path> --details

# Find large files
python cli.py code-metrics <path> --large <lines>

# Find complex files
python cli.py code-metrics <path> --complex <functions>

# Generate report
python cli.py code-metrics <path> --report <output_file>
```

### File Organizer
```bash
# Search by name
python cli.py file-organizer <directory> --name <pattern>

# Search by extension
python cli.py file-organizer <directory> --ext <extension>

# Search by size
python cli.py file-organizer <directory> --size <min> <max>

# Search by date
python cli.py file-organizer <directory> --days <N>

# Organize files
python cli.py file-organizer <directory> --organize <target> --execute

# Find duplicates
python cli.py file-organizer <directory> --duplicates
```

---

## Performance Tips

1. **Large Files**: For very large log files (>1GB), consider splitting them first:
   ```bash
   split -l 100000 large.log chunk_
   python cli.py log-analyzer chunk_aa
   ```

2. **Recursive Scans**: Use specific paths instead of root to speed up scans:
   ```bash
   # Slower
   python cli.py code-metrics /

   # Faster
   python cli.py code-metrics ./src
   ```

3. **Batch Processing**: Process multiple files in a loop:
   ```bash
   for file in *.log; do
       python cli.py log-analyzer "$file" --report "reports/$file.txt"
   done
   ```

---

## Troubleshooting

### Common Issues

1. **Permission Denied**: Make sure the CLI has read permissions:
   ```bash
   chmod +r /path/to/file
   ```

2. **Memory Issues**: For very large files, process in chunks:
   ```bash
   python cli.py data-transform large.json output.csv --json-to-csv
   ```

3. **Encoding Errors**: Specify encoding if needed (modify the tool):
   ```python
   with open(file, 'r', encoding='utf-8') as f:
       # file reading
   ```

---

## Conclusion

These tools are designed to handle real-world developer workflows efficiently. By using terminal-based automation, you can:

- **Save Time**: No need to switch between multiple apps
- **Automate**: Integrate into scripts and CI/CD pipelines
- **Scale**: Handle large datasets and files
- **Customize**: Modify tools for your specific needs

Start with the examples above and adapt them to your specific use cases!
