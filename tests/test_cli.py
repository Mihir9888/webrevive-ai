import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cli")))

from click.testing import CliRunner

from webrevive_cli.main import cli


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "WebRevive AI" in result.output
    assert "scan" in result.output
    assert "analyze" in result.output
    assert "report" in result.output
    assert "init" in result.output


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.0.0" in result.output


def test_scan_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--help"])
    assert result.exit_code == 0
    assert "--output" in result.output
    assert "--severity" in result.output
    assert "--wcag" in result.output


def test_analyze_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["analyze", "--help"])
    assert result.exit_code == 0
    assert "--model" in result.output
    assert "--ollama-url" in result.output


def test_report_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["report", "--help"])
    assert result.exit_code == 0
    assert "--format" in result.output
    assert "--output" in result.output


def test_report_execution(tmp_path):
    runner = CliRunner()
    sample_file = tmp_path / "sample_results.json"
    sample_file.write_text(
        json.dumps({
            "url": "https://test.example",
            "title": "Unit Test Page",
            "violations": [],
            "passes": [],
        }),
        encoding="utf-8",
    )

    out_file = tmp_path / "output.html"
    result = runner.invoke(
        cli,
        ["report", str(sample_file), "--format", "html", "--output", str(out_file)],
    )
    assert result.exit_code == 0
    assert out_file.exists()
    assert "WebRevive AI" in out_file.read_text(encoding="utf-8")
