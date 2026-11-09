"""Tests for accessibility scanner service and language plugins."""

import pytest
from app.services.scanner import AccessibilityScanner
from app.plugins.html_plugin import HTMLPlugin
from app.plugins.react_plugin import ReactPlugin
from app.plugins.vue_plugin import VuePlugin
from app.plugins.angular_plugin import AngularPlugin
from app.plugins.registry import plugin_registry


def test_parse_axe_results() -> None:
    """Verify that parse_axe_results transforms axe output into expected dictionary format."""
    scanner = AccessibilityScanner()
    raw_axe_results = {
        "violations": [
            {
                "id": "image-alt",
                "impact": "critical",
                "description": "Images must have alternate text",
                "help": "Provide meaningful alternate text",
                "helpUrl": "https://dequeuniversity.com/rules/axe/4.9/image-alt",
                "tags": ["wcag2a", "wcag111"],
                "nodes": [
                    {
                        "html": '<img src="banner.jpg">',
                        "target": ["body > div > img"],
                        "failureSummary": "Element does not have an alt attribute",
                    }
                ],
            }
        ]
    }

    parsed = scanner.parse_axe_results(raw_axe_results)
    assert len(parsed) == 1
    issue = parsed[0]
    assert issue["rule_id"] == "image-alt"
    assert issue["impact"] == "critical"
    assert issue["html_source"] == '<img src="banner.jpg">'
    assert issue["css_selector"] == "body > div > img"
    assert "wcag111" in issue["wcag_tags"]


def test_html_heuristic_scan() -> None:
    """Verify static heuristic scanner identifies missing alt, missing lang, and empty buttons."""
    scanner = AccessibilityScanner()
    sample_html = """
    <html>
      <head><title>Test Page</title></head>
      <body>
        <img src="test.png">
        <button></button>
        <input type="text" id="username">
      </body>
    </html>
    """

    issues = scanner._scan_html_heuristics(sample_html)
    rule_ids = [i["rule_id"] for i in issues]

    assert "html-has-lang" in rule_ids
    assert "image-alt" in rule_ids
    assert "button-name" in rule_ids
    assert "label" in rule_ids


def test_language_detection() -> None:
    """Test file path language detection via plugin registry."""
    assert plugin_registry.detect_language("index.html") == "html"
    assert plugin_registry.detect_language("src/App.jsx") == "react"
    assert plugin_registry.detect_language("src/Header.tsx") == "react"
    assert plugin_registry.detect_language("components/UserCard.vue") == "vue"
    assert plugin_registry.detect_language("app/home.component.html") == "angular"


def test_html_plugin_remediation() -> None:
    """Test HTMLPlugin fix application."""
    plugin = HTMLPlugin()
    original_html = '<div class="banner"><img src="logo.png"></div>'
    fix = {
        "original_code": '<img src="logo.png">',
        "suggested_code": '<img src="logo.png" alt="Company Logo">',
    }

    result = plugin.apply_fix(original_html, fix)
    assert 'alt="Company Logo"' in result


def test_react_plugin_remediation() -> None:
    """Test ReactPlugin fixes JSX class to className and adds accessibility attributes."""
    plugin = ReactPlugin()
    original_jsx = '<button class="btn" onClick={handleClick}></button>'
    fix = {
        "original_code": '<button class="btn" onClick={handleClick}></button>',
        "suggested_code": '<button class="btn" onClick={handleClick} aria-label="Close modal"></button>',
    }

    result = plugin.apply_fix(original_jsx, fix)
    assert 'className="btn"' in result
    assert 'aria-label="Close modal"' in result
