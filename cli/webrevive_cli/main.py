"""WebRevive CLI - Main Entry Point.

Command line interface for WebRevive AI - Web Accessibility and Content Refactoring System.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Optional

import click
import httpx
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from webrevive_cli import __version__
from webrevive_cli.commands.analyze import analyze_cmd
from webrevive_cli.commands.report import report_cmd
from webrevive_cli.commands.scan import scan_cmd

if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()

CONFIG_DIR = Path.home() / ".webrevive"
CONFIG_FILE = CONFIG_DIR / "config.json"

BANNER = r"""
 [bold cyan]__        __   _     ____            _            [/bold cyan][bold magenta]_     ___ [/bold magenta]
 [bold cyan]\ \      / /__| |__ |  _ \ _____   _(_)_   _____  [/bold cyan][bold magenta]/ \   |_ _|[/bold magenta]
 [bold cyan] \ \ /\ / / _ \ '_ \| |_) / _ \ \ / / \ \ / / _ \ [/bold cyan][bold magenta]/ _ \   | | [/bold magenta]
 [bold cyan]  \ V  V /  __/ |_) |  _ <  __/\ V /| |\ V /  __/ [/bold cyan][bold magenta]/ ___ \  | | [/bold magenta]
 [bold cyan]   \_/\_/ \___|_.__/|_| \_\___| \_/ |_| \_/ \___|[/bold cyan][bold magenta]/_/   \_\___|[/bold magenta]
"""


@click.group()
@click.version_option(version=__version__, prog_name="webrevive")
def cli() -> None:
    """WebRevive AI - Autonomous Accessibility & Content Refactoring CLI.

    Scan websites for WCAG 2.1/2.2 violations, analyze issues with local
    Ollama AI models, and produce comprehensive remediation reports.
    """
    pass


@cli.command(name="init")
@click.option(
    "--ollama-url",
    default="http://localhost:11434",
    help="Ollama instance URL to configure.",
)
@click.option(
    "--model",
    default="qwen2.5-coder:7b",
    help="Default LLM model for refactoring.",
)
def init_cmd(ollama_url: str, model: str) -> None:
    """Initialize WebRevive environment and verify system dependencies."""
    console.print(BANNER)
    console.print("[dim]Checking system requirements and dependencies...[/dim]\n")

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    default_config = {
        "version": __version__,
        "ollama_url": ollama_url,
        "default_model": model,
        "timeout": 30,
        "axe_cdn": "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js",
    }
    CONFIG_FILE.write_text(json.dumps(default_config, indent=2), encoding="utf-8")

    # Diagnostic Checks
    table = Table(
        title="WebRevive AI System Diagnostics",
        box=box.ROUNDED,
        header_style="bold magenta",
    )
    table.add_column("Component", style="cyan", width=22)
    table.add_column("Status", width=18)
    table.add_column("Details", width=42)

    # 1. Python Check
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 10)
    table.add_row(
        "Python Runtime",
        "[green][OK] Ready[/green]" if py_ok else "[red][FAIL] Incompatible[/red]",
        f"Version {py_ver} (Requires >= 3.10)",
    )

    # 2. Playwright Check
    try:
        import playwright
        pw_ver = playwright.__version__
        table.add_row(
            "Playwright Library",
            "[green][OK] Installed[/green]",
            f"Version {pw_ver}",
        )
    except ImportError:
        table.add_row(
            "Playwright Library",
            "[red][FAIL] Missing[/red]",
            "Run 'pip install playwright'",
        )

    # 3. Chromium Browser Binary
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser_ver = browser.version
            browser.close()
        table.add_row(
            "Chromium Browser",
            "[green][OK] Ready[/green]",
            f"Chromium v{browser_ver}",
        )
    except Exception:
        table.add_row(
            "Chromium Browser",
            "[yellow][WARN] Action Needed[/yellow]",
            "Run 'playwright install chromium'",
        )

    # 4. Ollama Connectivity
    ollama_ok = False
    models_found = []
    try:
        resp = httpx.get(f"{ollama_url.rstrip('/')}/api/tags", timeout=3.0)
        if resp.status_code == 200:
            ollama_ok = True
            models_found = [m.get("name") for m in resp.json().get("models", [])]
    except Exception:
        pass

    if ollama_ok:
        has_model = any(model in m for m in models_found)
        table.add_row(
            "Ollama Service",
            "[green][OK] Online[/green]",
            f"Endpoint: {ollama_url}",
        )
        table.add_row(
            f"AI Model ({model})",
            "[green][OK] Ready[/green]" if has_model else "[yellow][WARN] Not Downloaded[/yellow]",
            f"Available: {', '.join(models_found) if models_found else 'none'}. Run 'ollama pull {model}'",
        )
    else:
        table.add_row(
            "Ollama Service",
            "[yellow][WARN] Offline[/yellow]",
            f"Cannot connect to {ollama_url}. Run 'ollama serve'",
        )

    console.print(table)
    console.print(
        Panel(
            f"[bold green][OK] Configuration initialized at:[/bold green] {CONFIG_FILE.resolve()}\n\n"
            "[bold]Next Steps:[/bold]\n"
            "  * Scan a webpage: [cyan]webrevive scan https://example.com[/cyan]\n"
            "  * Analyze with AI: [cyan]webrevive analyze --url https://example.com[/cyan]\n"
            "  * Generate HTML audit: [cyan]webrevive report results.json --format html[/cyan]",
            title="[bold blue]Setup Complete[/bold blue]",
            border_style="blue",
        )
    )


# Register subcommands
cli.add_command(scan_cmd)
cli.add_command(analyze_cmd)
cli.add_command(report_cmd)
cli.add_command(init_cmd)


if __name__ == "__main__":
    cli()
