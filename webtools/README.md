# WebTools CLI - Terminal Ops Toolkit

A unified terminal toolkit for **web automation**, **network diagnostics**, and a bridge into sibling **DevTools** — one CLI hub instead of jumping between scripts.

## Features

### Web
- **Web Scraper** - Fast scraping with requests & BeautifulSoup
- **Content Extractor** - Extract code, scripts, emails, phones, tables
- **Link Analyzer** - Analyze and crawl links, check for broken links
- **Web Insights** - SEO, performance, security, and accessibility analysis
- **Form Automation** - Automate form submissions and logins
- **Browser Automation** - Headless/headed browser control with Playwright
- **Workflow Automation** - Chain multiple automation steps

### Network (diagnostics)
- **DNS lookup** - A/AAAA + reverse PTR (optional MX/NS/TXT via `dig`)
- **HTTP inspect** - Status, timing, headers, redirects (Network-panel style)
- **TLS inspect** - Certificate subject, issuer, expiry, SANs, cipher
- **Port / service check** - Single-port connectivity for named services
- **RDAP** - Public domain registration summary
- **Full report** - One command runs the stack above

### DevTools bridge
- Proxies to `../devtools/` so you can run log analysis, code metrics, data transform, and file organizer from the same CLI (`devtools`, `logs`, `metrics`, `transform`, `files`)

## Why Terminal-Based Web Automation?

**Advantages over GUI browsers:**
- **10x Faster**: No UI rendering overhead
- **Resource Efficient**: Lower CPU and memory usage
- **Scriptable**: Easy to automate and integrate into pipelines
- **Precise**: Programmatic control over every action
- **Batch Processing**: Handle multiple URLs efficiently
- **No Detection**: Less likely to be detected as a bot

## Installation

### Prerequisites
- Python 3.7 or higher

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# For browser automation (optional)
pip install playwright
playwright install

# Make CLI executable (optional)
chmod +x cli.py
```

## Usage

### Main CLI Entry Point

```bash
python cli.py <command> [arguments]
```

### Quick Start Examples

```bash
# Interactive menu
python cli.py menu

# Scrape a website
python cli.py scrape https://example.com --summary

# Extract email addresses
python cli.py content https://example.com --emails

# Analyze website insights
python cli.py insights https://example.com --score

# Crawl links
python cli.py links https://example.com --crawl 2

# List forms
python cli.py forms https://example.com --list-forms

# Network full report (DNS + HTTP + TLS + RDAP)
python cli.py network example.com

# DNS / HTTP / TLS
python cli.py dns example.com
python cli.py http https://example.com --method HEAD
python cli.py tls example.com
python cli.py port example.com https

# DevTools via bridge
python cli.py logs ../devtools/sample.log
python cli.py metrics . --details
```

## Detailed Commands

### 1. Web Scraper

Fast web scraping using requests and BeautifulSoup.

```bash
# Basic scrape
python cli.py scrape https://example.com

# Extract specific items
python cli.py scrape https://example.com --extract title,meta,links,images

# Show summary only
python cli.py scrape https://example.com --summary

# Save to JSON
python cli.py scrape https://example.com --output data.json

# Show all links
python cli.py scrape https://example.com --links

# Show headings
python cli.py scrape https://example.com --headings
```

**Extract options:**
- `title` - Page title
- `meta` - Meta tags
- `links` - All links
- `images` - All images
- `text` - Page text content
- `headings` - H1-H6 headings
- `forms` - All forms

### 2. Content Extractor

Extract specific content types from web pages.

```bash
# Extract everything
python cli.py content https://example.com --all

# Extract JavaScript
python cli.py content https://example.com --scripts

# Extract CSS
python cli.py content https://example.com --styles

# Extract code blocks
python cli.py content https://example.com --code

# Extract tables
python cli.py content https://example.com --tables

# Extract email addresses
python cli.py content https://example.com --emails

# Extract phone numbers
python cli.py content https://example.com --phones

# Extract URLs
python cli.py content https://example.com --urls

# Extract prices
python cli.py content https://example.com --prices

# Extract dates
python cli.py content https://example.com --dates

# Extract meta tags
python cli.py content https://example.com --meta

# Extract JSON-LD
python cli.py content https://example.com --json-ld
```

### 3. Link Analyzer

Analyze and crawl website links.

```bash
# Analyze links on single page
python cli.py links https://example.com

# Crawl links (depth 2)
python cli.py links https://example.com --crawl 2

# Limit pages crawled
python cli.py links https://example.com --crawl 2 --max-pages 20

# Check for broken links
python cli.py links https://example.com --check-broken

# Export links to JSON
python cli.py links https://example.com --export links.json

# Export as sitemap
python cli.py links https://example.com --sitemap sitemap.txt
```

### 4. Web Insights

Comprehensive website analysis.

```bash
# Full analysis
python cli.py insights https://example.com

# SEO analysis only
python cli.py insights https://example.com --seo

# Performance analysis only
python cli.py insights https://example.com --performance

# Structure analysis only
python cli.py insights https://example.com --structure

# Security analysis only
python cli.py insights https://example.com --security

# Content analysis only
python cli.py insights https://example.com --content

# Accessibility analysis only
python cli.py insights https://example.com --accessibility

# Show scores
python cli.py insights https://example.com --score

# Save report
python cli.py insights https://example.com --output report.json
```

**Analysis includes:**
- **SEO**: Title, meta description, headings, images with alt text
- **Performance**: Response time, page size, status code
- **Structure**: HTML5, semantic tags, scripts, styles
- **Security**: HTTPS, mixed content, insecure forms
- **Content**: Word count, reading time
- **Accessibility**: Lang attribute, alt text, form labels

### 5. Form Automation

Automate web form submissions.

```bash
# List all forms on page
python cli.py forms https://example.com --list-forms

# Submit form by index
python cli.py forms https://example.com --submit 0 --data '{"name":"John","email":"john@example.com"}'

# Submit form from JSON file
python cli.py forms https://example.com --submit 0 --data-file form_data.json

# Automate login
python cli.py forms https://example.com/login --login \
  --username myuser \
  --password mypass
```

### 6. Browser Automation

Control browsers (headless or headed) with Playwright.

```bash
# Headless browser (default)
python cli.py browser https://example.com

# Headed browser (visible)
python cli.py browser https://example.com --headed

# Take screenshot
python cli.py browser https://example.com --screenshot page.png

# Full page screenshot
python cli.py browser https://example.com --screenshot page.png --full-page

# Click element
python cli.py browser https://example.com --click "#submit-button"

# Fill input field
python cli.py browser https://example.com --fill "#name" "John Doe"

# Select dropdown option
python cli.py browser https://example.com --select "#country" "US"

# Wait for element
python cli.py browser https://example.com --wait-for "#content"

# Execute JavaScript
python cli.py browser https://example.com --evaluate "document.title"

# Extract links
python cli.py browser https://example.com --extract-links

# Extract forms
python cli.py browser https://example.com --extract-forms

# Execute workflow from file
python cli.py browser https://example.com --workflow workflow.json
```

### 7. Workflow Automation

Chain multiple automation steps.

```bash
# Execute workflow from JSON file
python cli.py workflow automation_plan.json

# Show workflow context after execution
python cli.py workflow automation_plan.json --context
```

**Workflow file format:**
```json
[
  {
    "action": "variable",
    "name": "base_url",
    "value": "https://example.com"
  },
  {
    "action": "scrape",
    "url": "https://example.com",
    "save_as": "page_data"
  },
  {
    "action": "extract",
    "from": "page_data",
    "path": "links",
    "save_as": "links"
  },
  {
    "action": "save",
    "from": "links",
    "filename": "links.json"
  }
]
```

**Available workflow actions:**
- `http_request` - Make HTTP request
- `scrape` - Scrape web page
- `extract` - Extract data from context
- `transform` - Transform data (filter, map, count)
- `save` - Save data to file
- `load` - Load data from file
- `variable` - Set variable
- `condition` - Conditional execution
- `loop` - Loop over items
- `wait` - Wait for seconds
- `log` - Log message

## Project Structure

```
webtools/
├── cli.py                          # Main CLI entry point
├── scrapers/
│   ├── web_scraper.py             # Fast web scraping
│   └── content_extractor.py       # Content extraction
├── analyzers/
│   ├── link_analyzer.py           # Link analysis
│   └── web_insights.py            # Website insights
├── automation/
│   ├── form_automation.py         # Form automation
│   ├── browser_automation.py      # Browser automation
│   └── workflow_automation.py     # Workflow automation
├── requirements.txt               # Dependencies
└── README.md                      # This file
```

## Real-World Use Cases

### 1. Competitive Analysis
```bash
# Analyze competitor's SEO
python cli.py insights https://competitor.com --seo --score

# Extract their product data
python cli.py scrape https://competitor.com/products --extract title,links --output products.json
```

### 2. Lead Generation
```bash
# Extract email addresses from a page
python cli.py content https://example.com --emails --output emails.json

# Crawl multiple pages and extract contacts
python cli.py links https://example.com --crawl 2 --export links.json
```

### 3. Price Monitoring
```bash
# Extract prices from e-commerce site
python cli.py content https://shop.com/products --prices --output prices.json

# Monitor price changes (schedule with cron)
```

### 4. SEO Auditing
```bash
# Complete SEO audit
python cli.py insights https://example.com --seo --output seo_report.json

# Check for broken links
python cli.py links https://example.com --check-broken
```

### 5. Automated Testing
```bash
# Test form submission
python cli.py forms https://example.com/contact --submit 0 \
  --data '{"name":"Test","email":"test@example.com"}'

# Test login flow
python cli.py forms https://example.com/login --login \
  --username testuser --password testpass
```

### 6. Data Migration
```bash
# Scrape old website data
python cli.py scrape https://oldsite.com --all --output old_data.json

# Transform and migrate to new system
python cli.py workflow migration_workflow.json
```

## Advanced Examples

### Multi-Step Data Extraction Workflow

Create `extract_data.json`:
```json
[
  {
    "action": "variable",
    "name": "target_url",
    "value": "https://example.com"
  },
  {
    "action": "scrape",
    "url": "https://example.com",
    "extract": ["title", "links", "text"],
    "save_as": "page_data"
  },
  {
    "action": "extract",
    "from": "page_data",
    "path": "links",
    "save_as": "all_links"
  },
  {
    "action": "transform",
    "from": "all_links",
    "operation": "filter",
    "field": "internal",
    "value": "true",
    "save_as": "internal_links"
  },
  {
    "action": "save",
    "from": "internal_links",
    "filename": "internal_links.json"
  }
]
```

Execute:
```bash
python cli.py workflow extract_data.json
```

### Automated Screenshot Generation

```bash
# Take screenshots of multiple pages
for url in https://example.com https://example.com/about https://example.com/contact; do
  python cli.py browser $url --screenshot "$(echo $url | sed 's/https\///g' | sed 's/\//_/g').png"
done
```

### Daily Website Health Check

Create cron job:
```bash
# Run daily at 9 AM
0 9 * * * /path/to/webtools/daily_check.sh
```

`daily_check.sh`:
```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d)
cd /path/to/webtools

# Check main site
python cli.py insights https://example.com --score --output "reports/main_$DATE.json"

# Check for broken links
python cli.py links https://example.com --check-broken --output "reports/links_$DATE.json"

# Send alert if score is low
SCORE=$(python cli.py insights https://example.com --score | grep "Overall" | awk '{print $3}')
if [ ${SCORE%.*} -lt 70 ]; then
  echo "Website score is low: $SCORE" | mail -s "Alert: Low Website Score" admin@example.com
fi
```

## Performance Tips

1. **Use requests for simple scraping** - Much faster than browser automation
2. **Limit crawl depth** - Don't crawl too deep (max 2-3 levels)
3. **Cache results** - Save data to avoid re-scraping
4. **Use sessions** - Reuse connections for multiple requests
5. **Parallel processing** - Process multiple URLs concurrently

## Troubleshooting

### Common Issues

1. **Import errors**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Playwright not installed**:
   ```bash
   pip install playwright
   playwright install
   ```

3. **SSL certificate errors**:
   ```python
   # Add to your script if needed
   import urllib3
   urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
   ```

4. **Timeout errors**:
   - Increase timeout in the code
   - Check your internet connection
   - Verify the URL is accessible

5. **403 Forbidden errors**:
   - The site may be blocking automated requests
   - Try adding headers to mimic a real browser
   - Use browser automation instead of requests

## Best Practices

1. **Respect robots.txt** - Check if scraping is allowed
2. **Rate limiting** - Don't overwhelm servers
3. **User agents** - Use appropriate user-agent strings
4. **Error handling** - Always handle network errors gracefully
5. **Data validation** - Validate scraped data before using
6. **Legal compliance** - Ensure scraping complies with Terms of Service

## Comparison: Terminal vs GUI Browser

| Aspect | GUI Browser | Terminal Tools |
|--------|-------------|----------------|
| Speed | Slow (UI rendering) | Fast (no UI) |
| Resources | High (CPU, RAM) | Low |
| Automation | Difficult | Easy (scripts) |
| Batch Processing | Manual | Automated |
| Precision | Manual clicks | Programmatic |
| Detection | Low | Medium |
| Learning Curve | Easy | Moderate |

## Future Enhancements

Potential additions:
- Proxy support
- CAPTCHA handling
- JavaScript rendering
- API integration
- Database export
- Scheduled tasks
- Webhook notifications
- Machine learning integration

## Contributing

Feel free to extend these tools for your specific needs. Each tool is modular and can be enhanced independently.

## License

Free to use and modify for any purpose. Use responsibly and respect website Terms of Service.
