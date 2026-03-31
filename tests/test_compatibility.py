"""Tests for the compatibility module."""

import pytest

from dotsync.compatibility import CompatibilityChecker, DEFAULT_PLATFORMS
from dotsync.models import DotfileAnalysis, Dependency, Severity


@pytest.fixture
def checker() -> CompatibilityChecker:
    return CompatibilityChecker()


@pytest.fixture
def sample_analysis() -> DotfileAnalysis:
    return DotfileAnalysis(
        path="/test/.zshrc",
        file_type="zsh",
        dependencies=[
            Dependency(name="starship", dependency_type="package"),
            Dependency(name="fzf", dependency_type="package"),
            Dependency(name="brew", dependency_type="package"),
        ],
        environment_variables={"EDITOR": "nvim"},
        aliases={"ll": "ls -la"},
        functions=["mkcd"],
    )


class TestCompatibilityChecker:
    """Tests for CompatibilityChecker."""

    def test_load_default_platforms(self, checker: CompatibilityChecker) -> None:
        assert "macos" in checker.platforms
        assert "linux-ubuntu" in checker.platforms
        assert "linux-arch" in checker.platforms
        assert "linux-fedora" in checker.platforms

    def test_platform_definition_structure(self, checker: CompatibilityChecker) -> None:
        macos = checker.platforms["macos"]
        assert macos.package_manager == "brew"
        assert macos.os_family == "darwin"
        assert "brew" not in macos.incompatible_tools

    def test_check_compatibility_macos_to_ubuntu(
        self, checker: CompatibilityChecker, sample_analysis: DotfileAnalysis
    ) -> None:
        issues = checker.check_compatibility(
            [sample_analysis], "linux-ubuntu", "macos"
        )
        # Should detect brew as incompatible
        brew_issues = [i for i in issues if "brew" in i.message.lower()]
        assert len(brew_issues) > 0

    def test_check_compatibility_unknown_platform(
        self, checker: CompatibilityChecker, sample_analysis: DotfileAnalysis
    ) -> None:
        with pytest.raises(ValueError):
            checker.check_compatibility([sample_analysis], "unknown-platform")

    def test_get_package_mapping(self, checker: CompatibilityChecker) -> None:
        # fd maps to fd-find on Ubuntu
        mapping = checker.get_package_mapping("fd", "linux-ubuntu")
        assert mapping == "fd-find"

    def test_get_install_command(self, checker: CompatibilityChecker) -> None:
        cmd = checker.get_install_command("starship", "linux-ubuntu")
        assert "apt install" in cmd

    def test_get_install_command_brew(self, checker: CompatibilityChecker) -> None:
        cmd = checker.get_install_command("starship", "macos")
        assert "brew install" in cmd

    def test_detect_current_platform(self, checker: CompatibilityChecker) -> None:
        platform = checker.detect_current_platform()
        # Should return a valid platform name
        assert platform in checker.platforms or platform == "unknown"

    def test_incompatible_tools_detection(
        self, checker: CompatibilityChecker, sample_analysis: DotfileAnalysis
    ) -> None:
        issues = checker.check_compatibility(
            [sample_analysis], "linux-ubuntu", "macos"
        )
        # Should have at least one error for incompatible tools
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) > 0
