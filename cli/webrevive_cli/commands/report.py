"""WebRevive CLI - Report Command.

Generates comprehensive, standalone accessibility reports in HTML, Markdown, or JSON.
Includes embedded responsive CSS, WCAG compliance scorecards, and violation breakdowns.
"""

from __future__ import annotations

import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from rich.console import Console

from webrevive_cli.commands.scan import calculate_health_score

if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()


def compute_statistics(data: Dict[str, Any]) -> Dict[str, Any]:
    """Compute summary metrics from scan data."""
    violations = data.get("violations", [])
    passes = data.get("passes", [])
    incomplete = data.get("incomplete", [])
    inapplicable = data.get("inapplicable", [])

    counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
    for v in violations:
        impact = (v.get("impact") or "moderate").lower()
        if impact in counts:
            counts[impact] += 1
        else:
            counts["moderate"] += 1

    health_score = calculate_health_score(violations, len(passes))

    return {
        "total_violations": len(violations),
        "total_passes": len(passes),
        "total_incomplete": len(incomplete),
        "total_inapplicable": len(inapplicable),
        "health_score": health_score,
        "critical_count": counts["critical"],
        "serious_count": counts["serious"],
        "moderate_count": counts["moderate"],
        "minor_count": counts["minor"],
    }


def generate_html_report(data: Dict[str, Any], title: Optional[str] = None) -> str:
    """Generate a self-contained HTML accessibility audit report with embedded CSS."""
    stats = compute_statistics(data)
    url = data.get("url") or data.get("requested_url") or "Unknown URL"
    page_title = data.get("title") or "WebRevive Accessibility Audit"
    report_title = title or f"Accessibility Audit: {page_title}"
    timestamp = data.get("timestamp") or datetime.now(timezone.utc).isoformat()
    violations: List[Dict[str, Any]] = data.get("violations", [])

    score = stats["health_score"]
    score_class = "score-high" if score >= 80 else ("score-mid" if score >= 50 else "score-low")

    # Build violation cards
    violation_cards_html = []
    if not violations:
        violation_cards_html.append(
            """
            <div class="card empty-state">
                <h3>🎉 Zero Accessibility Violations Detected</h3>
                <p>The audited page successfully conformed to all evaluated automated accessibility criteria.</p>
            </div>
            """
        )
    else:
        for idx, v in enumerate(violations, 1):
            impact = (v.get("impact") or "moderate").lower()
            rule_id = html.escape(v.get("id", "unknown"))
            help_desc = html.escape(v.get("help", ""))
            description = html.escape(v.get("description", ""))
            help_url = v.get("helpUrl", "")
            tags = v.get("tags", [])
            tag_badges = "".join(f'<span class="badge tag-badge">{html.escape(t)}</span>' for t in tags)

            node_items = []
            for node_idx, node in enumerate(v.get("nodes", []), 1):
                target = html.escape(" > ".join(node.get("target", ["body"])))
                snippet = html.escape(node.get("html", ""))
                summary = html.escape(node.get("failureSummary", ""))
                node_items.append(
                    f"""
                    <div class="node-box">
                        <div class="node-header">
                            <span class="node-index">Target #{node_idx}</span>
                            <code>{target}</code>
                        </div>
                        {f'<pre class="code-snippet"><code>{snippet}</code></pre>' if snippet else ''}
                        {f'<div class="failure-summary"><strong>Axe Diagnostic:</strong> {summary}</div>' if summary else ''}
                    </div>
                    """
                )

            nodes_html = "".join(node_items)

            violation_cards_html.append(
                f"""
                <article class="violation-card severity-{impact}">
                    <div class="violation-header">
                        <div class="header-main">
                            <span class="severity-badge badge-{impact}">{impact.upper()}</span>
                            <h3 class="rule-title">{rule_id}</h3>
                        </div>
                        <div class="help-link">
                            {f'<a href="{help_url}" target="_blank" rel="noopener noreferrer">Deque Documentation ↗</a>' if help_url else ''}
                        </div>
                    </div>
                    <p class="violation-desc">{help_desc}</p>
                    <p class="violation-subdesc">{description}</p>
                    <div class="tag-row">{tag_badges}</div>
                    <div class="nodes-container">
                        <details open>
                            <summary>Failing Elements ({len(v.get("nodes", []))} occurrence{'' if len(v.get("nodes", [])) == 1 else 's'})</summary>
                            <div class="nodes-list">{nodes_html}</div>
                        </details>
                    </div>
                </article>
                """
            )

    cards_joined = "\n".join(violation_cards_html)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(report_title)}</title>
    <style>
        :root {{
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #1e293b;
            --border-color: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-cyan: #38bdf8;
            --accent-purple: #818cf8;
            --critical-color: #ef4444;
            --serious-color: #f97316;
            --moderate-color: #eab308;
            --minor-color: #38bdf8;
            --success-color: #22c55e;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            --code-font: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: var(--bg-primary);
            color: var(--text-primary);
            font-family: var(--font-family);
            line-height: 1.5;
            padding: 2rem 1rem;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}
        header.header {{
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        }}
        .logo-row {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 0.5rem;
        }}
        .logo-badge {{
            background: linear-gradient(90deg, #38bdf8, #818cf8);
            color: #0f172a;
            font-weight: 800;
            font-size: 0.85rem;
            padding: 4px 10px;
            border-radius: 6px;
            letter-spacing: 0.5px;
        }}
        h1.title {{
            font-size: 1.8rem;
            font-weight: 700;
            color: #fff;
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 0.75rem;
            margin-top: 1.25rem;
            padding-top: 1.25rem;
            border-top: 1px solid var(--border-color);
            font-size: 0.9rem;
            color: var(--text-secondary);
        }}
        .meta-grid strong {{ color: var(--text-primary); }}
        .meta-grid a {{ color: var(--accent-cyan); text-decoration: none; word-break: break-all; }}
        .meta-grid a:hover {{ text-decoration: underline; }}
        
        /* Stats Dashboard */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .stat-card {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 1.25rem;
            text-align: center;
            transition: transform 0.2s ease;
        }}
        .stat-card:hover {{ transform: translateY(-2px); }}
        .stat-number {{
            font-size: 2.2rem;
            font-weight: 800;
            margin-top: 0.25rem;
        }}
        .stat-label {{
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-secondary);
        }}
        .score-high {{ color: var(--success-color); }}
        .score-mid {{ color: var(--moderate-color); }}
        .score-low {{ color: var(--critical-color); }}
        
        .c-critical {{ color: var(--critical-color); }}
        .c-serious {{ color: var(--serious-color); }}
        .c-moderate {{ color: var(--moderate-color); }}
        .c-minor {{ color: var(--minor-color); }}
        .c-passes {{ color: var(--success-color); }}

        /* Violations List */
        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--border-color);
        }}
        .section-title {{
            font-size: 1.3rem;
            font-weight: 600;
        }}
        .violation-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-left: 5px solid #64748b;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1.25rem;
        }}
        .violation-card.severity-critical {{ border-left-color: var(--critical-color); }}
        .violation-card.severity-serious {{ border-left-color: var(--serious-color); }}
        .violation-card.severity-moderate {{ border-left-color: var(--moderate-color); }}
        .violation-card.severity-minor {{ border-left-color: var(--minor-color); }}

        .violation-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
        }}
        .header-main {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        .severity-badge {{
            font-size: 0.75rem;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 4px;
            text-transform: uppercase;
        }}
        .badge-critical {{ background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid var(--critical-color); }}
        .badge-serious {{ background: rgba(249, 115, 22, 0.2); color: #fdba74; border: 1px solid var(--serious-color); }}
        .badge-moderate {{ background: rgba(234, 179, 8, 0.2); color: #fde047; border: 1px solid var(--moderate-color); }}
        .badge-minor {{ background: rgba(56, 189, 248, 0.2); color: #7dd3fc; border: 1px solid var(--minor-color); }}

        .rule-title {{
            font-size: 1.15rem;
            color: #fff;
        }}
        .help-link a {{
            color: var(--accent-cyan);
            font-size: 0.85rem;
            text-decoration: none;
        }}
        .help-link a:hover {{ text-decoration: underline; }}

        .violation-desc {{
            color: #e2e8f0;
            font-weight: 500;
            margin-bottom: 0.25rem;
        }}
        .violation-subdesc {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-bottom: 0.75rem;
        }}
        .tag-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
            margin-bottom: 1rem;
        }}
        .tag-badge {{
            background: #334155;
            color: #cbd5e1;
            font-size: 0.75rem;
            padding: 2px 8px;
            border-radius: 4px;
        }}

        /* Failing Nodes */
        details summary {{
            cursor: pointer;
            color: var(--accent-cyan);
            font-weight: 600;
            font-size: 0.95rem;
            margin-bottom: 0.5rem;
            outline: none;
        }}
        .nodes-list {{
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            margin-top: 0.75rem;
        }}
        .node-box {{
            background: #090d16;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 0.85rem;
        }}
        .node-header {{
            display: flex;
            align-items: baseline;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
            font-size: 0.85rem;
        }}
        .node-index {{
            background: #2563eb;
            color: white;
            font-size: 0.7rem;
            font-weight: 700;
            padding: 1px 6px;
            border-radius: 3px;
        }}
        .node-header code {{
            color: #a5f3fc;
            font-family: var(--code-font);
            word-break: break-all;
        }}
        pre.code-snippet {{
            background: #030712;
            border: 1px solid #1f2937;
            border-radius: 4px;
            padding: 0.5rem 0.75rem;
            overflow-x: auto;
            margin-bottom: 0.5rem;
        }}
        pre.code-snippet code {{
            font-family: var(--code-font);
            font-size: 0.82rem;
            color: #f1f5f9;
        }}
        .failure-summary {{
            font-size: 0.82rem;
            color: #fca5a5;
            line-height: 1.4;
        }}
        .empty-state {{
            padding: 3rem;
            text-align: center;
            background: var(--bg-secondary);
            border-radius: 8px;
            border: 1px dashed var(--border-color);
        }}
        footer.footer {{
            text-align: center;
            margin-top: 3rem;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border-color);
            color: var(--text-secondary);
            font-size: 0.85rem;
        }}
        footer.footer a {{ color: var(--accent-cyan); text-decoration: none; }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="logo-row">
                <span class="logo-badge">WebRevive AI</span>
                <span style="color: var(--text-secondary); font-size: 0.9rem;">Automated Accessibility Audit</span>
            </div>
            <h1 class="title">{html.escape(report_title)}</h1>
            <div class="meta-grid">
                <div><strong>Target URL:</strong> <a href="{html.escape(url)}" target="_blank" rel="noopener noreferrer">{html.escape(url)}</a></div>
                <div><strong>Audited At:</strong> {html.escape(timestamp)}</div>
                <div><strong>Engine:</strong> axe-core {html.escape(data.get("axe_version", "4.9.1"))} + Playwright</div>
            </div>
        </header>

        <!-- Stats Overview -->
        <section class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Health Score</div>
                <div class="stat-number {score_class}">{stats["health_score"]}<span style="font-size: 1.2rem;">/100</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Critical Issues</div>
                <div class="stat-number c-critical">{stats["critical_count"]}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Serious Issues</div>
                <div class="stat-number c-serious">{stats["serious_count"]}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Moderate Issues</div>
                <div class="stat-number c-moderate">{stats["moderate_count"]}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Minor Issues</div>
                <div class="stat-number c-minor">{stats["minor_count"]}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Passed Rules</div>
                <div class="stat-number c-passes">{stats["total_passes"]}</div>
            </div>
        </section>

        <!-- Violations Section -->
        <section>
            <div class="section-header">
                <h2 class="section-title">Violations Breakdown ({stats["total_violations"]})</h2>
            </div>
            {cards_joined}
        </section>

        <footer class="footer">
            <p>Generated by <strong>WebRevive AI</strong> &bull; Accessible, Local-First Content Refactoring</p>
        </footer>
    </div>
</body>
</html>
"""


def generate_markdown_report(data: Dict[str, Any], title: Optional[str] = None) -> str:
    """Generate clean Markdown accessibility audit report."""
    stats = compute_statistics(data)
    url = data.get("url") or data.get("requested_url") or "Unknown URL"
    page_title = data.get("title") or "WebRevive Accessibility Audit"
    report_title = title or f"Accessibility Audit: {page_title}"
    timestamp = data.get("timestamp") or datetime.now(timezone.utc).isoformat()
    violations: List[Dict[str, Any]] = data.get("violations", [])

    lines = [
        f"# {report_title}\n",
        f"- **Audited URL:** [{url}]({url})",
        f"- **Date & Time:** `{timestamp}`",
        f"- **Engine:** `axe-core {data.get('axe_version', '4.9.1')}` + Playwright Headless",
        f"- **Accessibility Health Score:** **{stats['health_score']}/100**\n",
        "## Executive Summary\n",
        "| Metric | Count |",
        "| :--- | :--- |",
        f"| **Overall Health Score** | **{stats['health_score']} / 100** |",
        f"| 🔴 Critical Severity | {stats['critical_count']} |",
        f"| 🟠 Serious Severity | {stats['serious_count']} |",
        f"| 🟡 Moderate Severity | {stats['moderate_count']} |",
        f"| 🔵 Minor Severity | {stats['minor_count']} |",
        f"| **Total Violations** | **{stats['total_violations']}** |",
        f"| 🟢 Passed Checks | {stats['total_passes']} |",
        f"| ⚪ Inapplicable Rules | {stats['total_inapplicable']} |\n",
        "## Detailed Violations Breakdown\n",
    ]

    if not violations:
        lines.append("🎉 **No accessibility violations detected!** The page meets all automated checks.\n")
    else:
        for idx, v in enumerate(violations, 1):
            impact = (v.get("impact") or "moderate").upper()
            rule_id = v.get("id", "unknown-rule")
            help_desc = v.get("help", "")
            description = v.get("description", "")
            help_url = v.get("helpUrl", "")
            tags = ", ".join(f"`{t}`" for t in v.get("tags", []))

            lines.append(f"### {idx}. [{impact}] `{rule_id}`")
            lines.append(f"**Description:** {help_desc} — *{description}*")
            if help_url:
                lines.append(f"**Reference:** [Deque Documentation]({help_url})")
            lines.append(f"**WCAG Tags:** {tags}\n")

            nodes = v.get("nodes", [])
            lines.append(f"**Affected Elements ({len(nodes)}):**\n")
            for n_idx, node in enumerate(nodes[:5], 1):
                target = " > ".join(node.get("target", []))
                html_snippet = node.get("html", "")
                summary = node.get("failureSummary", "")
                lines.append(f"*{n_idx}. Target Selector:* `{target}`")
                if html_snippet:
                    lines.append(f"```html\n{html_snippet}\n```")
                if summary:
                    lines.append(f"> **Axe Diagnostic:** {summary}\n")

            if len(nodes) > 5:
                lines.append(f"*... and {len(nodes) - 5} more occurrences.*")

            lines.append("\n---\n")

    lines.append("\n*Report produced autonomously by WebRevive AI.*")
    return "\n".join(lines)


@click.command(name="report")
@click.argument("results_file", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--format",
    "-f",
    type=click.Choice(["html", "md", "json"], case_sensitive=False),
    default="html",
    help="Report output format (html, md, or json).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Target file path to save report. Defaults to report.<format>.",
)
@click.option(
    "--title",
    type=str,
    default=None,
    help="Custom title for generated report.",
)
def report_cmd(
    results_file: str,
    format: str,
    output: Optional[str],
    title: Optional[str],
) -> None:
    """Generate comprehensive accessibility audit reports from scan results.

    Examples:
        webrevive report scan-results.json --format html --output audit.html
        webrevive report scan-results.json --format md --output audit.md
    """
    try:
        with open(results_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        console.print(f"[bold red]Failed to read results file:[/bold red] {exc}")
        sys.exit(1)

    fmt = format.lower()
    default_filename = f"webrevive-report.{fmt if fmt != 'md' else 'md'}"
    out_file = Path(output or default_filename)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "html":
        content = generate_html_report(data, title=title)
        out_file.write_text(content, encoding="utf-8")
    elif fmt == "md":
        content = generate_markdown_report(data, title=title)
        out_file.write_text(content, encoding="utf-8")
    elif fmt == "json":
        stats = compute_statistics(data)
        enriched = {
            "summary_statistics": stats,
            **data,
        }
        out_file.write_text(json.dumps(enriched, indent=2), encoding="utf-8")

    console.print(f"[bold green][OK] {fmt.upper()} report successfully generated:[/bold green] {out_file.resolve()}")


if __name__ == "__main__":
    report_cmd()
