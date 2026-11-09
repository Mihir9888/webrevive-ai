"""CLI commands for WebRevive."""

from webrevive_cli.commands.analyze import analyze_cmd
from webrevive_cli.commands.report import report_cmd
from webrevive_cli.commands.scan import scan_cmd

__all__ = ["scan_cmd", "analyze_cmd", "report_cmd"]
