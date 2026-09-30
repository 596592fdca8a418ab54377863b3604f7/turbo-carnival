# WebTools CLI - Practical Usage Examples

This document provides real-world scenarios and examples of when and how to use each tool in the WebTools CLI suite for terminal-based web automation.

## Table of Contents
1. [Web Scraper Examples](#web-scraper-examples)
2. [Content Extractor Examples](#content-extractor-examples)
3. [Link Analyzer Examples](#link-analyzer-examples)
4. [Web Insights Examples](#web-insights-examples)
5. [Form Automation Examples](#form-automation-examples)
6. [Browser Automation Examples](#browser-automation-examples)
7. [Workflow Automation Examples](#workflow-automation-examples)
8. [Integration & Automation Examples](#integration--automation-examples)

---

## Web Scraper Examples

### Scenario 1: Quick Website Overview

**Problem**: You need a quick overview of a website's structure and content.

**Solution**:
```bash
python cli.py scrape https://example.com --summary
```

**Results**:
- Page title: "Example Domain"
- Meta tags: 1
- Links: 1 (Internal: 0, External: 1)
- Text length: 182 characters

### Scenario 2: Extract All Page Data

**Problem**: You need complete data from a page for analysis.

**Solution**:
```bash
python cli.py scrape https://example.com --extract title,meta,links,images,text,headings,forms \
  --output page_data.json
```

**Use Cases**:
- Content migration
- SEO analysis
- Data backup
- Competitor analysis

### Scenario 3: Extract Only Links

**Problem**: You need all links from a page for crawling or analysis.

**Solution**:
```bash
python cli.py scrape https://example.com --links
```

**Results**:
- Shows all links with text and URLs
- Marks internal vs external links
- Easy to pipe to other tools

### Scenario 4: Extract Headings Structure

**Problem**: You need to understand the document structure (H1-H6).

**Solution**:
```bash
python cli.py scrape https://example.com --headings
```

**Use Cases**:
- Content structure analysis
- Table of contents generation
- SEO heading audit

---

## Content Extractor Examples

### Scenario 1: Extract Contact Information

**Problem**: Find all email addresses and phone numbers on a contact page.

**Solution**:
```bash
python cli.py content https://example.com/contact --emails --phones
```

**Results**:
- Lists all email addresses found
- Lists all phone numbers found
- Saves to JSON if needed

### Scenario 2: Extract Product Prices

**Problem**: Monitor prices on an e-commerce site.

**Solution**:
```bash
python cli.py content https://shop.com/products --prices --output prices.json
```

**Use Cases**:
- Price monitoring
- Competitor price tracking
- Historical price analysis

### Scenario 3: Extract Code Examples

**Problem**: Extract code blocks from a documentation site.

**Solution**:
```bash
python cli.py content https://docs.example.com --code --output code_blocks.json
```

**Results**:
- Extracts all `<pre>` and `<code>` blocks
- Includes language information
- Preserves formatting

### Scenario 4: Extract Tables

**Problem**: Extract data tables for analysis.

**Solution**:
```bash
python cli.py content https://example.com/data --tables --output tables.json
```

**Results**:
- Extracts all tables with headers
- Preserves row structure
- Easy to convert to CSV

### Scenario 5: Extract All Content

**Problem**: Complete content extraction for archiving.

**Solution**:
```bash
python cli.py content https://example.com --all --output full_content.json
```

**Includes**:
- Scripts (inline and external)
- Styles (inline and external)
- Code blocks
- Tables
- Emails, phones, URLs
- Prices, dates
- Meta tags
- JSON-LD structured data

---

## Link Analyzer Examples

### Scenario 1: Basic Link Analysis

**Problem**: Analyze link structure of a single page.

**Solution**:
```bash
python cli.py links https://example.com
```

**Results**:
- Total links count
- Internal vs external links
- Top external domains
- Top link texts

### Scenario 2: Crawl Website

**Problem**: Crawl entire website to map structure.

**Solution**:
```bash
python cli.py links https://example.com --crawl 2 --max-pages 50
```

**Parameters**:
- `--crawl 2`: Crawl 2 levels deep
- `--max-pages 50`: Limit to 50 pages

**Use Cases**:
- Site mapping
- SEO analysis
- Content inventory

### Scenario 3: Find Broken Links

**Problem**: Identify broken links on your website.

**Solution**:
```bash
python cli.py links https://example.com --check-broken
```

**Results**:
- Lists all broken links (404, 500, etc.)
- Shows link text and URL
- Helps with link maintenance

### Scenario 4: Generate Sitemap

**Problem**: Create a sitemap for your website.

**Solution**:
```bash
python cli.py links https://example.com --crawl 2 --sitemap sitemap.txt
```

**Results**:
- Plain text file with all URLs
- One URL per line
- Ready for search engines

### Scenario 5: Export Links for Analysis

**Problem**: Export links for further analysis in other tools.

**Solution**:
```bash
python cli.py links https://example.com --export links.json
```

**Results**:
- JSON file with all link data
- Includes URL, text, internal/external flag
- Easy to process with other tools

---

## Web Insights Examples

### Scenario 1: Complete Website Audit

**Problem**: Comprehensive analysis of website health.

**Solution**:
```bash
python cli.py insights https://example.com --score
```

**Analysis Includes**:
- SEO (title, meta, headings, images)
- Performance (response time, page size)
- Structure (HTML5, semantic tags)
- Security (HTTPS, mixed content)
- Content (word count, reading time)
- Accessibility (alt text, form labels)

**Results**:
- Detailed report for each category
- Overall score (0-100)
- Specific issues and recommendations

### Scenario 2: SEO Audit Only

**Problem**: Focus on SEO optimization.

**Solution**:
```bash
python cli.py insights https://example.com --seo --output seo_report.json
```

**SEO Checks**:
- Title tag presence and length
- Meta description presence and length
- Heading structure (H1, H2, H3)
- Image alt text
- Internal/external link ratio

### Scenario 3: Performance Analysis

**Problem**: Identify performance bottlenecks.

**Solution**:
```bash
python cli.py insights https://example.com --performance
```

**Metrics**:
- Response time (ms)
- Page size (KB)
- Status code
- Performance issues

### Scenario 4: Security Check

**Problem**: Basic security assessment.

**Solution**:
```bash
python cli.py insights https://example.com --security
```

**Security Checks**:
- HTTPS usage
- Mixed content detection
- Insecure forms
- Security best practices

### Scenario 5: Accessibility Audit

**Problem**: Check basic accessibility compliance.

**Solution**:
```bash
python cli.py insights https://example.com --accessibility
```

**Accessibility Checks**:
- HTML lang attribute
- Image alt text
- Form labels
- Basic WCAG compliance

---

## Form Automation Examples

### Scenario 1: List All Forms

**Problem**: Understand what forms are available on a page.

**Solution**:
```bash
python cli.py forms https://example.com/contact --list-forms
```

**Results**:
- Form action URLs
- Form methods (GET/POST)
- All input fields with types
- Textarea and select fields
- Required field indicators

### Scenario 2: Submit Contact Form

**Problem**: Automate contact form submission for testing.

**Solution**:
```bash
python cli.py forms https://example.com/contact --submit 0 \
  --data '{"name":"John Doe","email":"john@example.com","message":"Test message"}'
```

**Use Cases**:
- Form testing
- Automated submissions
- Data entry automation

### Scenario 3: Automate Login

**Problem**: Automate login process for authenticated scraping.

**Solution**:
```bash
python cli.py forms https://example.com/login --login \
  --username myuser \
  --password mypass
```

**Use Cases**:
- Automated testing
- Authenticated scraping
- Workflow automation

### Scenario 4: Submit Form from File

**Problem**: Submit form with data from JSON file.

**Solution**:
```bash
# Create form_data.json
cat > form_data.json << EOF
{
  "name": "John Doe",
  "email": "john@example.com",
  "subject": "Inquiry",
  "message": "Test message"
}
EOF

# Submit form
python cli.py forms https://example.com/contact --submit 0 --data-file form_data.json
```

---

## Browser Automation Examples

### Scenario 1: Take Screenshot

**Problem**: Capture visual representation of a page.

**Solution**:
```bash
# Headless screenshot
python cli.py browser https://example.com --screenshot page.png

# Full page screenshot
python cli.py browser https://example.com --screenshot full_page.png --full-page

# Visible browser screenshot
python cli.py browser https://example.com --headed --screenshot visible.png
```

**Use Cases**:
- Visual testing
- Page archiving
- Design verification
- Documentation

### Scenario 2: Automate Multi-Step Process

**Problem**: Navigate through a multi-step form process.

**Solution**:
```bash
python cli.py browser https://example.com/form \
  --fill "#name" "John Doe" \
  --fill "#email" "john@example.com" \
  --select "#country" "US" \
  --click "#next-button" \
  --wait 2 \
  --click "#submit-button"
```

### Scenario 3: Extract Dynamic Content

**Problem**: Extract content that requires JavaScript rendering.

**Solution**:
```bash
python cli.py browser https://example.com/dynamic \
  --wait-for "#dynamic-content" \
  --extract-links
```

**Use Cases**:
- Single Page Applications (SPAs)
- JavaScript-heavy sites
- Dynamic content loading

### Scenario 4: Execute JavaScript

**Problem**: Run custom JavaScript on a page.

**Solution**:
```bash
python cli.py browser https://example.com \
  --evaluate "document.title" \
  --evaluate "window.scrollY"
```

### Scenario 5: Workflow from File

**Problem**: Execute complex browser automation from JSON file.

**Solution**:
```bash
# Create browser_workflow.json
cat > browser_workflow.json << EOF
[
  {"action": "navigate", "value": "https://example.com"},
  {"action": "click", "selector": "#login-button"},
  {"action": "fill", "selector": "#username", "value": "myuser"},
  {"action": "fill", "selector": "#password", "value": "mypass"},
  {"action": "click", "selector": "#submit"},
  {"action": "wait_for", "selector": "#dashboard"},
  {"action": "screenshot", "value": "dashboard.png"}
]
EOF

# Execute workflow
python cli.py browser https://example.com --workflow browser_workflow.json
```

---

## Workflow Automation Examples

### Scenario 1: Multi-Step Data Extraction

**Problem**: Scrape multiple pages and extract specific data.

**Solution**:
```json
[
  {
    "action": "variable",
    "name": "urls",
    "value": ["https://example.com/page1", "https://example.com/page2"]
  },
  {
    "action": "scrape",
    "url": "https://example.com/page1",
    "save_as": "page1_data"
  },
  {
    "action": "scrape",
    "url": "https://example.com/page2",
    "save_as": "page2_data"
  },
  {
    "action": "extract",
    "from": "page1_data",
    "path": "title",
    "save_as": "title1"
  },
  {
    "action": "extract",
    "from": "page2_data",
    "path": "title",
    "save_as": "title2"
  },
  {
    "action": "save",
    "from": "page1_data",
    "filename": "page1.json"
  },
  {
    "action": "save",
    "from": "page2_data",
    "filename": "page2.json"
  }
]
```

Execute:
```bash
python cli.py workflow multi_page_extraction.json
```

### Scenario 2: Conditional Processing

**Problem**: Process data differently based on conditions.

**Solution**:
```json
[
  {
    "action": "scrape",
    "url": "https://example.com",
    "save_as": "page_data"
  },
  {
    "action": "extract",
    "from": "page_data",
    "path": "title",
    "save_as": "title"
  },
  {
    "action": "condition",
    "if": "title=Example Domain",
    "then": [
      {
        "action": "log",
        "message": "This is the example domain"
      }
    ],
    "else": [
      {
        "action": "log",
        "message": "This is a different domain"
      }
    ]
  }
]
```

### Scenario 3: Loop Through Items

**Problem**: Process multiple items from a list.

**Solution**:
```json
[
  {
    "action": "scrape",
    "url": "https://example.com/products",
    "save_as": "products_page"
  },
  {
    "action": "extract",
    "from": "products_page",
    "path": "links",
    "save_as": "product_links"
  },
  {
    "action": "loop",
    "over": "product_links",
    "steps": [
      {
        "action": "log",
        "message": "Processing link:",
        "from": "item.url"
      },
      {
        "action": "scrape",
        "url": "{{item.url}}",
        "save_as": "product_data"
      },
      {
        "action": "save",
        "from": "product_data",
        "filename": "product_{{index}}.json"
      }
    ]
  }
]
```

### Scenario 4: Data Transformation Pipeline

**Problem**: Transform scraped data into different formats.

**Solution**:
```json
[
  {
    "action": "scrape",
    "url": "https://example.com/data",
    "save_as": "raw_data"
  },
  {
    "action": "extract",
    "from": "raw_data",
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
    "action": "transform",
    "from": "internal_links",
    "operation": "map",
    "field": "url",
    "save_as": "internal_urls"
  },
  {
    "action": "save",
    "from": "internal_urls",
    "filename": "internal_urls.txt",
    "format": "text"
  }
]
```

---

## Integration & Automation Examples

### Scenario 1: Daily Website Health Check

**Problem**: Automated daily monitoring of website health.

**Solution** (cron job):
```bash
# Add to crontab (runs daily at 8 AM)
0 8 * * * /path/to/webtools/daily_health_check.sh
```

**daily_health_check.sh**:
```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d)
cd /path/to/webtools

# Check main site
python cli.py insights https://example.com --score --output "reports/health_$DATE.json"

# Check for broken links
python cli.py links https://example.com --check-broken --output "reports/links_$DATE.json"

# Send alert if score is low
SCORE=$(python cli.py insights https://example.com --score | grep "Overall" | awk '{print $3}')
if [ ${SCORE%.*} -lt 70 ]; then
  echo "Website score is low: $SCORE" | mail -s "Alert: Low Website Score" admin@example.com
fi
```

### Scenario 2: Competitor Monitoring

**Problem**: Monitor competitor websites for changes.

**Solution**:
```bash
#!/bin/bash
COMPETITORS=("https://competitor1.com" "https://competitor2.com" "https://competitor3.com")
DATE=$(date +%Y-%m-%d)

for url in "${COMPETITORS[@]}"; do
  NAME=$(echo $url | sed 's/https\///g' | sed 's/\//_/g')
  python cli.py insights $url --seo --output "competitors/${NAME}_$DATE.json"
  python cli.py scrape $url --links --output "competitors/${NAME}_links_$DATE.json"
done
```

### Scenario 3: Price Monitoring Automation

**Problem**: Monitor product prices and alert on changes.

**Solution**:
```bash
#!/bin/bash
PRODUCT_URL="https://shop.com/product/123"
PRICE_FILE="current_price.txt"
ALERT_PRICE=100

# Extract current price
python cli.py content $PRODUCT_URL --prices --output prices.json
CURRENT_PRICE=$(cat prices.json | grep -oP '\d+\.\d{2}' | head -1)

# Check if price file exists
if [ -f "$PRICE_FILE" ]; then
  OLD_PRICE=$(cat "$PRICE_FILE")
  if [ "$CURRENT_PRICE" != "$OLD_PRICE" ]; then
    echo "Price changed from $OLD_PRICE to $CURRENT_PRICE" | mail -s "Price Alert" admin@example.com
  fi
fi

# Update price file
echo "$CURRENT_PRICE" > "$PRICE_FILE"

# Check if price is below alert threshold
if (( $(echo "$CURRENT_PRICE < $ALERT_PRICE" | bc -l) )); then
  echo "Price $CURRENT_PRICE is below alert threshold $ALERT_PRICE" | mail -s "Price Drop Alert" admin@example.com
fi
```

### Scenario 4: Automated Testing Pipeline

**Problem**: Integrate web automation into CI/CD pipeline.

**Solution** (GitHub Actions):
```yaml
name: Web Automation Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r webtools/requirements.txt
      - name: Test website health
        run: |
          cd webtools
          python cli.py insights https://example.com --score
      - name: Check for broken links
        run: |
          cd webtools
          python cli.py links https://example.com --check-broken
      - name: Test form submission
        run: |
          cd webtools
          python cli.py forms https://example.com/contact --list-forms
```

### Scenario 5: Content Migration

**Problem**: Migrate content from old website to new system.

**Solution**:
```bash
#!/bin/bash
OLD_SITE="https://oldsite.com"
NEW_SITE="https://newsite.com"

# Crawl old site
python cli.py links $OLD_SITE --crawl 2 --max-pages 100 --export old_links.json

# Extract content from each page
python cli.py workflow content_migration.json

# Transform and import to new system
# (Custom script to import data to new CMS)
```

**content_migration.json**:
```json
[
  {
    "action": "load",
    "filename": "old_links.json",
    "save_as": "links"
  },
  {
    "action": "transform",
    "from": "links",
    "operation": "map",
    "field": "url",
    "save_as": "urls"
  },
  {
    "action": "loop",
    "over": "urls",
    "steps": [
      {
        "action": "scrape",
        "url": "{{item}}",
        "extract": ["title", "text", "meta"],
        "save_as": "page_content"
      },
      {
        "action": "save",
        "from": "page_content",
        "filename": "migrated/page_{{index}}.json"
      }
    ]
  }
]
```

---

## Performance Tips

### 1. Use requests for simple scraping
```bash
# Fast (no browser overhead)
python cli.py scrape https://example.com

# Slower (browser overhead)
python cli.py browser https://example.com
```

### 2. Limit crawl depth
```bash
# Reasonable (2 levels)
python cli.py links https://example.com --crawl 2

# Potentially very slow (5+ levels)
python cli.py links https://example.com --crawl 5
```

### 3. Cache results
```bash
# Save results to avoid re-scraping
python cli.py scrape https://example.com --output cache.json

# Load from cache instead of re-scraping
python cli.py workflow use_cache.json
```

### 4. Use sessions for multiple requests
```bash
# The tools automatically use sessions for efficiency
# This is handled internally in the code
```

### 5. Parallel processing
```bash
# Process multiple URLs in parallel
for url in $(cat urls.txt); do
  python cli.py scrape $url --output "data/$(echo $url | md5sum).json" &
done
wait
```

---

## Troubleshooting

### Common Issues

1. **Import errors**:
   ```bash
   pip install -r requirements.txt
   ```

2. **SSL certificate errors**:
   ```python
   # Add to your script if needed
   import urllib3
   urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
   ```

3. **Timeout errors**:
   - Increase timeout in the code
   - Check your internet connection
   - Verify the URL is accessible

4. **403 Forbidden errors**:
   - The site may be blocking automated requests
   - Try adding headers to mimic a real browser
   - Use browser automation instead of requests

5. **JavaScript content not loading**:
   ```bash
   # Use browser automation for JavaScript-heavy sites
   python cli.py browser https://example.com --extract-links
   ```

---

## Best Practices

1. **Respect robots.txt** - Check if scraping is allowed
2. **Rate limiting** - Don't overwhelm servers with requests
3. **User agents** - Use appropriate user-agent strings
4. **Error handling** - Always handle network errors gracefully
5. **Data validation** - Validate scraped data before using
6. **Legal compliance** - Ensure scraping complies with Terms of Service
7. **Testing** - Test your workflows on a small scale first
8. **Logging** - Keep logs of your automation runs
9. **Backups** - Backup important scraped data
10. **Security** - Don't hardcode sensitive data in scripts

---

## Conclusion

These tools provide powerful terminal-based web automation capabilities that are:

- **10x Faster** than GUI browsers
- **Resource Efficient** - Low CPU and memory usage
- **Scriptable** - Easy to automate and integrate
- **Precise** - Programmatic control over every action
- **Batch Processing** - Handle multiple URLs efficiently

Start with the examples above and adapt them to your specific use cases. The terminal-based approach is often superior to web/mobile apps for web automation tasks!
