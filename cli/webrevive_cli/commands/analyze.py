"""WebRevive CLI - Analyze Command.

Analyzes accessibility scan violations using a local Ollama LLM instance
(e.g., Qwen 2.5 Coder or Llama 3) to generate human explanations and accessible code refactorings.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import httpx
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.rule import Rule

from webrevive_cli.commands.scan import (
    SEVERITY_STYLES,
    execute_playwright_scan,
    filter_violations,
    validate_url,
)

if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5-coder:7b"


def check_ollama_status(ollama_url: str) -> List[str]:
    """Check connectivity to Ollama server and list available models."""
    try:
        resp = httpx.get(f"{ollama_url.rstrip('/')}/api/tags", timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            return models
        return []
    except Exception:
        return []


def query_ollama(
    prompt: str,
    model: str,
    ollama_url: str,
    system_prompt: Optional[str] = None,
    timeout_sec: float = 90.0,
) -> str:
    """Send generation prompt to local Ollama API."""
    endpoint = f"{ollama_url.rstrip('/')}/api/generate"
    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "top_p": 0.9,
        },
    }
    if system_prompt:
        payload["system"] = system_prompt

    resp = httpx.post(endpoint, json=payload, timeout=timeout_sec)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Ollama returned HTTP {resp.status_code}: {resp.text}"
        )
    data = resp.json()
    return data.get("response", "").strip()


def build_analysis_prompt(violation: Dict[str, Any], page_url: str) -> str:
    """Construct an accessibility refactoring prompt for Ollama."""
    rule_id = violation.get("id", "accessibility-rule")
    impact = violation.get("impact", "unknown")
    help_text = violation.get("help", "")
    description = violation.get("description", "")
    tags = ", ".join(violation.get("tags", []))

    node_details = []
    for idx, node in enumerate(violation.get("nodes", [])[:3], 1):
        target = " > ".join(node.get("target", ["unknown"]))
        html = node.get("html", "")
        summary = node.get("failureSummary", "")
        node_details.append(
            f"Occurrence {idx}:\n"
            f"- Selector: `{target}`\n"
            f"- Failing HTML: `{html}`\n"
            f"- Axe Failure Diagnostic: {summary}"
        )

    nodes_str = "\n".join(node_details) if node_details else "No specific node details available."

    prompt = f"""
You are an expert accessibility engineer and senior frontend developer.
We scanned the web page at: {page_url}

Please analyze this WCAG accessibility violation and provide an actionable code fix:

### Violation Metadata
- Rule ID: {rule_id}
- Impact / Severity: {impact}
- Description: {description}
- Help: {help_text}
- WCAG Criteria Tags: {tags}

### Failing DOM Elements
{nodes_str}

### Instructions:
Provide your response using markdown with these 3 clear sections:
1. **Disability & User Impact**: In 2-3 sentences, explain specifically which users (e.g. screen reader users, keyboard-only navigators, color-blind individuals) are affected and how this breaks their experience.
2. **Root Cause**: Identify what attribute, contrast ratio, or structural element is missing or incorrect.
3. **Refactored Accessible Code**: Provide the exact corrected HTML/CSS/ARIA snippet that fixes this issue while adhering strictly to WCAG 2.1 AA/AAA standards. Include comments highlighting what was changed.
"""
    return prompt.strip()


@click.command(name="analyze")
@click.argument("results_file", required=False, type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--url",
    "-u",
    type=str,
    default=None,
    help="Target URL to scan and analyze in a single step.",
)
@click.option(
    "--model",
    "-m",
    type=str,
    default=DEFAULT_MODEL,
    help=f"Ollama model to use for refactoring (default: {DEFAULT_MODEL}).",
)
@click.option(
    "--ollama-url",
    type=str,
    default=DEFAULT_OLLAMA_URL,
    help=f"Base URL of local Ollama instance (default: {DEFAULT_OLLAMA_URL}).",
)
@click.option(
    "--limit",
    "-l",
    type=int,
    default=5,
    help="Maximum number of issues to analyze with AI (default: 5). Use 0 for all.",
)
@click.option(
    "--severity",
    "-s",
    type=click.Choice(["minor", "moderate", "serious", "critical"], case_sensitive=False),
    default=None,
    help="Filter issues by minimum severity level before analysis.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Optional file path to save AI analysis results (JSON or Markdown).",
)
def analyze_cmd(
    results_file: Optional[str],
    url: Optional[str],
    model: str,
    ollama_url: str,
    limit: int,
    severity: Optional[str],
    output: Optional[str],
) -> None:
    """Analyze accessibility violations and generate refactored code using local Ollama AI.

    Examples:
        webrevive analyze results.json
        webrevive analyze --url https://example.com --model qwen2.5-coder:7b
        webrevive analyze results.json --limit 3 --output fixes.md
    """
    if not results_file and not url:
        console.print(
            "[bold red]Error:[/bold red] You must specify either a [cyan]<results-file>[/cyan] or the [cyan]--url[/cyan] option."
        )
        sys.exit(1)

    # Verify Ollama server connectivity
    console.print(f"[dim]Checking Ollama service at {ollama_url}...[/dim]")
    available_models = check_ollama_status(ollama_url)
    if not available_models:
        console.print(
            Panel(
                f"[bold red]Cannot connect to Ollama at {ollama_url}[/bold red]\n\n"
                "To use AI refactoring features:\n"
                "1. Ensure Ollama is installed: [cyan]https://ollama.ai[/cyan]\n"
                "2. Start the Ollama server: [cyan]ollama serve[/cyan]\n"
                f"3. Pull the required model: [cyan]ollama pull {model}[/cyan]\n"
                "4. Re-run this command once the model is downloaded.",
                title="[red]Ollama Service Offline[/red]",
                border_style="red",
            )
        )
        sys.exit(1)

    # Check if target model is pulled
    model_match = any(m.startswith(model) or model.startswith(m) for m in available_models)
    if not model_match:
        console.print(
            f"[yellow]Warning: Model '{model}' not found in Ollama library.[/yellow]\n"
            f"Available models: {', '.join(available_models) if available_models else 'none'}\n"
            f"[dim]Attempting to invoke '{model}' (Ollama may automatically pull or error if missing)...[/dim]\n"
        )

    # Load or scan data
    scan_data: Dict[str, Any] = {}
    if url:
        valid_url = validate_url(url)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console,
        ) as progress:
            progress.add_task(f"Scanning {valid_url} before AI analysis...", total=None)
            scan_data = execute_playwright_scan(url=valid_url)
    else:
        assert results_file is not None
        try:
            with open(results_file, "r", encoding="utf-8") as f:
                scan_data = json.load(f)
        except Exception as exc:
            console.print(f"[bold red]Failed to read scan results file:[/bold red] {exc}")
            sys.exit(1)

    target_url = scan_data.get("url", "Unknown URL")
    violations = scan_data.get("violations", [])

    if severity:
        violations = filter_violations(violations, min_severity=severity)

    if not violations:
        console.print("[bold green]✓ No accessibility violations to analyze.[/bold green]")
        return

    # Cap analysis count
    target_violations = violations if limit <= 0 else violations[:limit]

    console.print(
        Panel(
            f"[bold cyan]Target URL:[/bold cyan] {target_url}\n"
            f"[bold cyan]Ollama Model:[/bold cyan] [bold green]{model}[/bold green]\n"
            f"[bold cyan]Violations to Analyze:[/bold cyan] {len(target_violations)} of {len(violations)} total",
            title="[bold blue]🤖 WebRevive AI - Code Refactoring & Analysis[/bold blue]",
            border_style="blue",
        )
    )

    system_prompt = (
        "You are WebRevive AI, an expert accessibility engineer and senior frontend developer. "
        "Your mission is to provide accurate, production-ready, accessible HTML/CSS/ARIA code "
        "solutions conforming to WCAG 2.1 AA/AAA standards."
    )

    ai_analyses: List[Dict[str, Any]] = []

    for idx, v in enumerate(target_violations, 1):
        rule_id = v.get("id", "rule")
        impact = (v.get("impact") or "moderate").lower()
        impact_style = SEVERITY_STYLES.get(impact, "white")

        console.print(Rule(f"Issue {idx}/{len(target_violations)}: [{impact_style}]{impact.upper()}[/{impact_style}] {rule_id}", style="cyan"))

        prompt = build_analysis_prompt(v, target_url)

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn(f"[bold yellow]Generating AI fix with {model}...[/bold yellow]"),
                transient=True,
                console=console,
            ) as progress:
                progress.add_task("query", total=None)
                ai_solution = query_ollama(
                    prompt=prompt,
                    model=model,
                    ollama_url=ollama_url,
                    system_prompt=system_prompt,
                )

            # Display formatted Markdown
            console.print(
                Panel(
                    Markdown(ai_solution),
                    title=f"[bold green]AI Remediation Plan for '{rule_id}'[/bold green]",
                    border_style="green",
                    padding=(1, 2),
                )
            )

            ai_analyses.append({
                "rule_id": rule_id,
                "impact": impact,
                "violation": v,
                "prompt": prompt,
                "ai_solution": ai_solution,
            })

        except Exception as exc:
            console.print(f"[bold red]Failed to get AI analysis for {rule_id}:[/bold red] {exc}")

    # Save output if requested
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output.endswith(".json"):
            report_data = {
                "url": target_url,
                "model": model,
                "timestamp": scan_data.get("timestamp"),
                "analyses": ai_analyses,
            }
            output_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
        else:
            # Markdown report
            md_lines = [
                f"# WebRevive AI - Remediation Report for {target_url}\n",
                f"- **Model:** `{model}`",
                f"- **Total Issues Analyzed:** {len(ai_analyses)}\n",
                "---\n",
            ]
            for item in ai_analyses:
                md_lines.append(f"## [{item['impact'].upper()}] Rule: {item['rule_id']}\n")
                md_lines.append(item["ai_solution"])
                md_lines.append("\n---\n")

            output_path.write_text("\n".join(md_lines), encoding="utf-8")

        console.print(f"\n[bold green]✓ AI analysis exported to:[/bold green] {output_path.resolve()}")


if __name__ == "__main__":
    analyze_cmd()
