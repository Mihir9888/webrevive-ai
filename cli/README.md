# WebRevive CLI

Autonomous command-line utility for scanning web applications for accessibility violations (WCAG 2.1/2.2 AA & AAA), generating remediation reports, and obtaining AI-driven refactored code fixes via local Ollama LLMs.

## Installation

```bash
pip install -e .
playwright install chromium
```

## Quick Start

```bash
# Scan a live website
webrevive scan https://example.com

# Scan and immediately generate AI fixes
webrevive analyze --url https://example.com

# Generate formatted HTML / Markdown audit reports
webrevive report results.json --format html --output audit.html
```
