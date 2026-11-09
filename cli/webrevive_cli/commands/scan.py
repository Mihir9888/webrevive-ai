"""WebRevive CLI - Scan Command.

Performs local, standalone accessibility scanning using Playwright and axe-core.
Does not require the WebRevive backend server.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import click
import httpx
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()

# Official Axe-Core CDN URL
AXE_CDN_URL = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js"
CACHE_DIR = Path.home() / ".webrevive" / "cache"
CACHED_AXE_PATH = CACHE_DIR / "axe.min.js"

SEVERITY_ORDER = {
    "critical": 4,
    "serious": 3,
    "moderate": 2,
    "minor": 1,
}

SEVERITY_STYLES = {
    "critical": "bold red",
    "serious": "red1",
    "moderate": "bold yellow",
    "minor": "cyan",
    "unknown": "white",
}


def ensure_axe_core_script() -> str:
    """Load axe-core source from local cache or fetch from CDN.

    Returns the axe.min.js JavaScript code.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if CACHED_AXE_PATH.exists() and CACHED_AXE_PATH.stat().st_size > 10000:
        try:
            return CACHED_AXE_PATH.read_text(encoding="utf-8")
        except Exception:
            pass

    # Attempt fetching from CDN
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(AXE_CDN_URL)
            if resp.status_code == 200 and len(resp.text) > 10000:
                CACHED_AXE_PATH.write_text(resp.text, encoding="utf-8")
                return resp.text
    except Exception as exc:
        console.print(
            f"[yellow]Warning: Could not fetch axe-core from CDN ({exc}). Falling back to browser script tag injection.[/yellow]"
        )

    return ""


def validate_url(url: str) -> str:
    """Validate and normalize target URL."""
    if not url.startswith(("http://", "https://", "file://")):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.netloc and not url.startswith("file://"):
        raise click.BadParameter(f"Invalid URL: {url}")
    return url


def calculate_health_score(violations: List[Dict[str, Any]], passes_count: int) -> int:
    """Calculate an accessibility compliance health score from 0 to 100."""
    if not violations and passes_count == 0:
        return 100

    penalty = 0
    for v in violations:
        impact = (v.get("impact") or "moderate").lower()
        node_count = max(len(v.get("nodes", [])), 1)
        if impact == "critical":
            penalty += 15 + (node_count * 3)
        elif impact == "serious":
            penalty += 10 + (node_count * 2)
        elif impact == "moderate":
            penalty += 5 + (node_count * 1)
        else:
            penalty += 2 + (node_count * 0.5)

    base = 100 - penalty
    return max(0, min(100, int(round(base))))


def execute_playwright_scan(
    url: str,
    wcag_filter: Optional[str] = None,
    timeout_sec: int = 30,
    wait_sec: int = 2,
    headless: bool = True,
) -> Dict[str, Any]:
    """Execute Playwright browser navigation and axe-core analysis."""
    try:
        from playwright.sync_api import Error as PlaywrightError, sync_playwright
    except ImportError:
        console.print(
            "[bold red]Error: Playwright is not installed.[/bold red]\n"
            "Run: [cyan]pip install playwright && playwright install chromium[/cyan]"
        )
        sys.exit(1)

    axe_source = ensure_axe_core_script()

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
        except PlaywrightError as exc:
            console.print(
                f"[bold red]Failed to launch Chromium:[/bold red] {exc}\n"
                "[yellow]Hint: Install browser binaries with:[/yellow] [cyan]playwright install chromium[/cyan]"
            )
            sys.exit(1)

        try:
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) WebRevive-AI-Auditor/1.0",
            )
            page = context.new_page()
            page.set_default_timeout(timeout_sec * 1000)

            # Navigate
            page.goto(url, wait_until="load")
            if wait_sec > 0:
                time.sleep(wait_sec)

            # Inject axe-core
            if axe_source:
                page.evaluate(axe_source)
            else:
                page.add_script_tag(url=AXE_CDN_URL)

            # Configure axe options
            axe_options: Dict[str, Any] = {}
            if wcag_filter:
                wcag_tags = [t.strip().lower() for t in wcag_filter.split(",")]
                axe_options["runOnly"] = {"type": "tag", "values": wcag_tags}

            options_json = json.dumps(axe_options)

            # Run Axe
            raw_results = page.evaluate(
                f"""
                async () => {{
                    if (typeof axe === 'undefined') {{
                        throw new Error('axe-core is not defined on the window object');
                    }}
                    const options = {options_json};
                    return await axe.run(document, options);
                }}
                """
            )

            # Capture page metadata
            title = page.title()
            final_url = page.url

            browser.close()

            return {
                "url": final_url,
                "requested_url": url,
                "title": title,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "axe_version": raw_results.get("testEngine", {}).get("version", "4.9.1"),
                "violations": raw_results.get("violations", []),
                "passes": raw_results.get("passes", []),
                "incomplete": raw_results.get("incomplete", []),
                "inapplicable": raw_results.get("inapplicable", []),
            }

        except PlaywrightError as exc:
            browser.close()
            console.print(f"[bold red]Playwright scanning error:[/bold red] {exc}")
            sys.exit(1)
        except Exception as exc:
            browser.close()
            console.print(f"[bold red]Unexpected error during scan:[/bold red] {exc}")
            sys.exit(1)


def filter_violations(
    violations: List[Dict[str, Any]],
    min_severity: Optional[str] = None,
    wcag_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Filter violation list by minimum impact and WCAG tags."""
    filtered = []
    min_rank = SEVERITY_ORDER.get((min_severity or "").lower(), 0)

    for item in violations:
        impact = (item.get("impact") or "moderate").lower()
        impact_rank = SEVERITY_ORDER.get(impact, 0)
        if impact_rank < min_rank:
            continue

        if wcag_filter:
            tags = [t.lower() for t in item.get("tags", [])]
            requested_tags = [t.strip().lower() for t in wcag_filter.split(",")]
            if not any(req in tags for req in requested_tags):
                continue

        filtered.append(item)

    # Sort descending by severity
    filtered.sort(
        key=lambda x: SEVERITY_ORDER.get((x.get("impact") or "moderate").lower(), 0),
        reverse=True,
    )
    return filtered


def render_rich_table(
    data: Dict[str, Any],
    filtered_violations: List[Dict[str, Any]],
    severity_filter: Optional[str] = None,
) -> None:
    """Render scan metrics and violations table using Rich."""
    url = data.get("url")
    title = data.get("title") or "Untitled Web Page"
    timestamp = data.get("timestamp")
    all_violations = data.get("violations", [])
    passes_count = len(data.get("passes", []))
    score = calculate_health_score(all_violations, passes_count)

    counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
    for v in all_violations:
        imp = (v.get("impact") or "moderate").lower()
        if imp in counts:
            counts[imp] += 1

    # Header Panel
    score_color = "green" if score >= 80 else ("yellow" if score >= 50 else "red")
    summary_text = (
        f"[bold cyan]URL:[/bold cyan] {url}\n"
        f"[bold cyan]Title:[/bold cyan] {title}\n"
        f"[bold cyan]Audited At:[/bold cyan] {timestamp}\n"
        f"[bold cyan]Health Score:[/bold cyan] [{score_color} bold]{score}/100[/{score_color} bold] | "
        f"[bold red]Critical: {counts['critical']}[/bold red] | "
        f"[bold red1]Serious: {counts['serious']}[/bold red1] | "
        f"[bold yellow]Moderate: {counts['moderate']}[/bold yellow] | "
        f"[bold cyan]Minor: {counts['minor']}[/bold cyan] | "
        f"[bold green]Passed: {passes_count}[/bold green]"
    )
    console.print(
        Panel(
            summary_text,
            title="[bold blue]🔍 WebRevive AI - Accessibility Scan Summary[/bold blue]",
            border_style="blue",
            expand=False,
        )
    )

    if not filtered_violations:
        console.print(
            "\n[bold green]No accessibility violations matching your criteria were found![/bold green]\n"
        )
        return

    # Violations Table
    table = Table(
        title=f"Detected Accessibility Violations ({len(filtered_violations)} displayed)",
        box=box.ROUNDED,
        header_style="bold magenta",
        show_lines=True,
    )
    table.add_column("Severity", justify="center", style="bold", width=12)
    table.add_column("Rule ID & Guidelines", width=24)
    table.add_column("Description & Help", width=38)
    table.add_column("Failing Selector & Element", width=42)

    for v in filtered_violations:
        impact = (v.get("impact") or "moderate").lower()
        style = SEVERITY_STYLES.get(impact, "white")
        rule_id = v.get("id", "unknown-rule")
        help_text = v.get("help", "")
        description = v.get("description", "")
        wcag_tags = [
            t for t in v.get("tags", []) if t.startswith("wcag") or t == "best-practice"
        ]
        tags_str = ", ".join(wcag_tags[:3]) if wcag_tags else "General"

        rule_cell = f"[bold]{rule_id}[/bold]\n[dim]{tags_str}[/dim]"
        desc_cell = f"{help_text}\n[dim]{description}[/dim]"

        nodes = v.get("nodes", [])
        if nodes:
            first_node = nodes[0]
            target_selector = " > ".join(first_node.get("target", ["body"]))
            html_snippet = first_node.get("html", "")
            if len(html_snippet) > 80:
                html_snippet = html_snippet[:77] + "..."
            node_cell = f"[cyan]{target_selector}[/cyan]\n[dim]{html_snippet}[/dim]"
            if len(nodes) > 1:
                node_cell += f"\n[yellow]+ {len(nodes) - 1} more occurrence(s)[/yellow]"
        else:
            node_cell = "[dim]No specific DOM node[/dim]"

        table.add_row(
            f"[{style}]{impact.upper()}[/{style}]",
            rule_cell,
            desc_cell,
            node_cell,
        )

    console.print(table)


@click.command(name="scan")
@click.argument("url")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["table", "json", "html"], case_sensitive=False),
    default="table",
    help="Display or output format (table, json, or html).",
)
@click.option(
    "--severity",
    "-s",
    type=click.Choice(["minor", "moderate", "serious", "critical"], case_sensitive=False),
    default=None,
    help="Filter issues by minimum severity level.",
)
@click.option(
    "--wcag",
    "-w",
    type=str,
    default=None,
    help="Filter by WCAG standard tag, e.g. 'wcag2a', 'wcag2aa', 'wcag21aa'.",
)
@click.option(
    "--save",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Optional file path to write full scan results (JSON).",
)
@click.option(
    "--timeout",
    type=int,
    default=30,
    help="Page navigation timeout in seconds (default: 30s).",
)
@click.option(
    "--wait",
    type=int,
    default=2,
    help="Additional wait time after page load for SPA rendering in seconds (default: 2s).",
)
@click.option(
    "--headless/--no-headless",
    default=True,
    help="Run browser in headless mode (default: True).",
)
def scan_cmd(
    url: str,
    output: str,
    severity: Optional[str],
    wcag: Optional[str],
    save: Optional[str],
    timeout: int,
    wait: int,
    headless: bool,
) -> None:
    """Scan a URL for accessibility issues using Playwright and axe-core.

    Example:
        webrevive scan https://example.com --severity serious --output table
        webrevive scan https://example.com --save scan-results.json
    """
    valid_url = validate_url(url)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task(f"Navigating to {valid_url} and running axe-core...", total=None)
        results = execute_playwright_scan(
            url=valid_url,
            wcag_filter=wcag,
            timeout_sec=timeout,
            wait_sec=wait,
            headless=headless,
        )

    # Process filtered violations
    all_violations = results.get("violations", [])
    filtered = filter_violations(all_violations, min_severity=severity, wcag_filter=wcag)
    results["filtered_violations"] = filtered
    results["filter_applied"] = {"severity": severity, "wcag": wcag}

    # Save to file if requested
    if save:
        save_path = Path(save)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        console.print(f"[bold green][OK] Full scan results saved to:[/bold green] {save_path.resolve()}")

    # Render according to output mode
    if output == "table":
        render_rich_table(results, filtered, severity_filter=severity)
    elif output == "json":
        click.echo(json.dumps(results, indent=2))
    elif output == "html":
        from webrevive_cli.commands.report import generate_html_report

        html_content = generate_html_report(results)
        click.echo(html_content)


if __name__ == "__main__":
    scan_cmd()
