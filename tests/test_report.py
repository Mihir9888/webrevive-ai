import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cli")))

from webrevive_cli.commands.report import (
    compute_statistics,
    generate_html_report,
    generate_markdown_report,
)
from webrevive_cli.commands.scan import calculate_health_score, filter_violations


def sample_scan_data():
    return {
        "url": "https://example.com/test",
        "title": "Test Audit Page",
        "timestamp": "2026-11-09T12:00:00Z",
        "axe_version": "4.9.1",
        "violations": [
            {
                "id": "color-contrast",
                "impact": "serious",
                "description": "Ensures the contrast between foreground and background colors meets WCAG 2 AA thresholds",
                "help": "Elements must meet minimum color contrast ratio thresholds",
                "helpUrl": "https://dequeuniversity.com/rules/axe/4.9/color-contrast",
                "tags": ["cat.color", "wcag2aa", "wcag143"],
                "nodes": [
                    {
                        "target": ["button.cta"],
                        "html": '<button class="cta">Submit</button>',
                        "failureSummary": "Element has insufficient color contrast of 2.1 (foreground color: #777, background color: #fff)",
                    }
                ],
            },
            {
                "id": "image-alt",
                "impact": "critical",
                "description": "Ensures <img> elements have alternate text or a role of none or presentation",
                "help": "Images must have alternate text",
                "helpUrl": "https://dequeuniversity.com/rules/axe/4.9/image-alt",
                "tags": ["cat.text-alternatives", "wcag2a", "wcag111", "section508"],
                "nodes": [
                    {
                        "target": ["img.hero"],
                        "html": '<img src="/hero.jpg" class="hero">',
                        "failureSummary": "Element does not have an alt attribute",
                    }
                ],
            },
        ],
        "passes": [
            {"id": "document-title", "description": "Ensures each HTML document contains a non-empty <title>"}
        ],
        "incomplete": [],
        "inapplicable": [],
    }


def test_calculate_health_score():
    data = sample_scan_data()
    score = calculate_health_score(data["violations"], len(data["passes"]))
    assert 0 <= score <= 100
    assert score < 100  # Because violations exist


def test_compute_statistics():
    data = sample_scan_data()
    stats = compute_statistics(data)
    assert stats["total_violations"] == 2
    assert stats["critical_count"] == 1
    assert stats["serious_count"] == 1
    assert stats["moderate_count"] == 0
    assert stats["minor_count"] == 0
    assert stats["total_passes"] == 1


def test_filter_violations():
    data = sample_scan_data()
    violations = data["violations"]

    critical_only = filter_violations(violations, min_severity="critical")
    assert len(critical_only) == 1
    assert critical_only[0]["id"] == "image-alt"

    wcag2aa_only = filter_violations(violations, wcag_filter="wcag2aa")
    assert len(wcag2aa_only) == 1
    assert wcag2aa_only[0]["id"] == "color-contrast"


def test_generate_html_report():
    data = sample_scan_data()
    html_output = generate_html_report(data)
    assert "<!DOCTYPE html>" in html_output
    assert "WebRevive AI" in html_output
    assert "color-contrast" in html_output
    assert "image-alt" in html_output
    assert "button.cta" in html_output


def test_generate_markdown_report():
    data = sample_scan_data()
    md_output = generate_markdown_report(data)
    assert "# Accessibility Audit" in md_output
    assert "color-contrast" in md_output
    assert "image-alt" in md_output
    assert "Critical" in md_output
