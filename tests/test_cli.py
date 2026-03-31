"""Tests for the CLI module."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dotsync.cli import app

runner = CliRunner()


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


class TestCLI:
    """Tests for CLI commands."""

    def test_version(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "DotSync v" in result.stdout

    def test_analyze(self, fixtures_dir: Path) -> None:
        result = runner.invoke(app, ["analyze", str(fixtures_dir)])
        assert result.exit_code == 0
        assert "Analysis Complete" in result.stdout
        assert "Files analyzed:" in result.stdout

    def test_analyze_nonexistent_path(self) -> None:
        result = runner.invoke(app, ["analyze", "/nonexistent/path"])
        assert result.exit_code == 1
        assert "Error" in result.stdout

    def test_check(self, fixtures_dir: Path) -> None:
        result = runner.invoke(app, ["check", "linux-ubuntu", "--path", str(fixtures_dir)])
        assert result.exit_code == 0
        assert "Compatibility Report" in result.stdout

    def test_generate(self, fixtures_dir: Path, tmp_path: Path) -> None:
        output = tmp_path / "migration.sh"
        result = runner.invoke(
            app, ["generate", "linux-ubuntu", "--path", str(fixtures_dir), "--output", str(output)]
        )
        assert result.exit_code == 0
        assert "Migration script generated" in result.stdout
        assert output.exists()

    def test_graph(self, fixtures_dir: Path, tmp_path: Path) -> None:
        output = tmp_path / "deps.mermaid"
        result = runner.invoke(
            app, ["graph", "--path", str(fixtures_dir), "--output", str(output)]
        )
        assert result.exit_code == 0
        assert "Dependency graph saved" in result.stdout
        assert output.exists()

    def test_conflicts(self, fixtures_dir: Path) -> None:
        result = runner.invoke(app, ["conflicts", "--path", str(fixtures_dir)])
        assert result.exit_code == 0
        # Should detect some conflicts from fixtures
        assert "Conflicts" in result.stdout or "No conflicts" in result.stdout

    def test_validate(self, fixtures_dir: Path) -> None:
        result = runner.invoke(app, ["validate", "--path", str(fixtures_dir)])
        assert result.exit_code == 0
        assert "Validation Results" in result.stdout or "passed validation" in result.stdout

    def test_export_json(self, fixtures_dir: Path) -> None:
        result = runner.invoke(app, ["export-report", "--path", str(fixtures_dir), "--format", "json"])
        assert result.exit_code == 0
        assert '"source_path"' in result.stdout

    def test_diff_same_dir(self, fixtures_dir: Path) -> None:
        result = runner.invoke(app, ["diff", str(fixtures_dir), str(fixtures_dir)])
        assert result.exit_code == 0
        assert "Dotfiles Comparison" in result.stdout
