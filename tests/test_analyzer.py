"""Tests for the analyzer module."""

from pathlib import Path

import pytest

from dotsync.analyzer import DotfileAnalyzer


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def analyzer(fixtures_dir: Path) -> DotfileAnalyzer:
    return DotfileAnalyzer(fixtures_dir)


class TestDotfileAnalyzer:
    """Tests for DotfileAnalyzer."""

    def test_analyze_all(self, analyzer: DotfileAnalyzer) -> None:
        analyses = analyzer.analyze_all()
        assert len(analyses) > 0

    def test_analyze_zshrc(self, analyzer: DotfileAnalyzer) -> None:
        analyses = analyzer.analyze_all()
        zshrc = next((a for a in analyses if ".zshrc" in a.path), None)
        assert zshrc is not None
        assert zshrc.file_type == "zsh"
        assert len(zshrc.dependencies) > 0
        assert len(zshrc.aliases) > 0
        assert len(zshrc.functions) > 0
        assert "EDITOR" in zshrc.environment_variables

    def test_analyze_bashrc(self, analyzer: DotfileAnalyzer) -> None:
        analyses = analyzer.analyze_all()
        bashrc = next((a for a in analyses if ".bashrc" in a.path), None)
        assert bashrc is not None
        assert bashrc.file_type == "bash"
        assert len(bashrc.dependencies) > 0

    def test_analyze_gitconfig(self, analyzer: DotfileAnalyzer) -> None:
        analyses = analyzer.analyze_all()
        gitconfig = next((a for a in analyses if ".gitconfig" in a.path), None)
        assert gitconfig is not None
        assert gitconfig.file_type == "gitconfig"
        # Should detect editor and include dependencies
        assert len(gitconfig.dependencies) > 0

    def test_analyze_tmux(self, analyzer: DotfileAnalyzer) -> None:
        analyses = analyzer.analyze_all()
        tmux = next((a for a in analyses if ".tmux.conf" in a.path), None)
        assert tmux is not None
        assert tmux.file_type == "tmux"
        assert len(tmux.dependencies) > 0

    def test_analyze_vimrc(self, analyzer: DotfileAnalyzer) -> None:
        analyses = analyzer.analyze_all()
        vimrc = next((a for a in analyses if ".vimrc" in a.path), None)
        assert vimrc is not None
        assert vimrc.file_type == "vim"
        assert len(vimrc.dependencies) > 0

    def test_analyze_starship_config(self, analyzer: DotfileAnalyzer) -> None:
        analyses = analyzer.analyze_all()
        starship = next((a for a in analyses if "starship.toml" in a.path), None)
        assert starship is not None
        assert starship.file_type == "toml"

    def test_analyze_vscode_settings(self, analyzer: DotfileAnalyzer) -> None:
        analyses = analyzer.analyze_all()
        vscode = next((a for a in analyses if "settings.json" in a.path), None)
        assert vscode is not None
        assert vscode.file_type == "json"

    def test_nonexistent_directory(self) -> None:
        analyzer = DotfileAnalyzer("/nonexistent/path")
        with pytest.raises(FileNotFoundError):
            analyzer.analyze_all()

    def test_extract_aliases(self, analyzer: DotfileAnalyzer) -> None:
        analyses = analyzer.analyze_all()
        zshrc = next((a for a in analyses if ".zshrc" in a.path), None)
        assert zshrc is not None
        assert "ll" in zshrc.aliases
        assert zshrc.aliases["ll"] == "ls -la"

    def test_extract_environment_variables(self, analyzer: DotfileAnalyzer) -> None:
        analyses = analyzer.analyze_all()
        zshrc = next((a for a in analyses if ".zshrc" in a.path), None)
        assert zshrc is not None
        assert zshrc.environment_variables.get("EDITOR") == "nvim"

    def test_extract_functions(self, analyzer: DotfileAnalyzer) -> None:
        analyses = analyzer.analyze_all()
        zshrc = next((a for a in analyses if ".zshrc" in a.path), None)
        assert zshrc is not None
        assert "mkcd" in zshrc.functions
        assert "extract" in zshrc.functions
