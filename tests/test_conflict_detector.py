"""Tests for the conflict detector module."""

import pytest

from dotsync.conflict_detector import ConflictDetector
from dotsync.models import DotfileAnalysis, Dependency, Severity


@pytest.fixture
def detector() -> ConflictDetector:
    return ConflictDetector()


@pytest.fixture
def conflicting_analyses() -> list[DotfileAnalysis]:
    return [
        DotfileAnalysis(
            path="/test/.zshrc",
            file_type="zsh",
            dependencies=[
                Dependency(name="starship", dependency_type="package"),
                Dependency(name="zoxide", dependency_type="package"),
                Dependency(name="fzf", dependency_type="package"),
            ],
            environment_variables={
                "EDITOR": "nvim",
                "PATH": "/usr/local/bin:$PATH",
            },
            aliases={"ll": "ls -la"},
            functions=["mkcd", "extract"],
        ),
        DotfileAnalysis(
            path="/test/.bashrc",
            file_type="bash",
            dependencies=[
                Dependency(name="powerlevel10k", dependency_type="plugin"),
                Dependency(name="autojump", dependency_type="package"),
            ],
            environment_variables={
                "EDITOR": "vim",
                "PATH": "/usr/bin:$PATH",
            },
            aliases={"ll": "ls -l"},
            functions=["mkcd"],
        ),
    ]


class TestConflictDetector:
    """Tests for ConflictDetector."""

    def test_detect_env_conflicts(
        self, detector: ConflictDetector, conflicting_analyses: list[DotfileAnalysis]
    ) -> None:
        conflicts = detector.detect_conflicts(conflicting_analyses)
        # Should detect EDITOR conflict
        editor_conflicts = [c for c in conflicts if c.affected_variable == "EDITOR"]
        assert len(editor_conflicts) > 0

    def test_detect_alias_conflicts(
        self, detector: ConflictDetector, conflicting_analyses: list[DotfileAnalysis]
    ) -> None:
        conflicts = detector.detect_conflicts(conflicting_analyses)
        # Should detect 'll' alias conflict
        alias_conflicts = [c for c in conflicts if c.affected_variable == "ll"]
        assert len(alias_conflicts) > 0

    def test_detect_function_conflicts(
        self, detector: ConflictDetector, conflicting_analyses: list[DotfileAnalysis]
    ) -> None:
        conflicts = detector.detect_conflicts(conflicting_analyses)
        # Should detect 'mkcd' function conflict
        func_conflicts = [c for c in conflicts if c.affected_variable == "mkcd"]
        assert len(func_conflicts) > 0

    def test_detect_tool_conflicts(
        self, detector: ConflictDetector, conflicting_analyses: list[DotfileAnalysis]
    ) -> None:
        conflicts = detector.detect_conflicts(conflicting_analyses)
        # Should detect directory jump tool conflict (zoxide vs autojump)
        tool_conflicts = [c for c in conflicts if "directory jump" in c.description.lower()]
        assert len(tool_conflicts) > 0

    def test_no_conflicts(self, detector: ConflictDetector) -> None:
        analyses = [
            DotfileAnalysis(
                path="/test/.zshrc",
                file_type="zsh",
                dependencies=[],
                environment_variables={},
                aliases={},
                functions=[],
            )
        ]
        conflicts = detector.detect_conflicts(analyses)
        assert len(conflicts) == 0

    def test_conflict_summary(
        self, detector: ConflictDetector, conflicting_analyses: list[DotfileAnalysis]
    ) -> None:
        detector.detect_conflicts(conflicting_analyses)
        summary = detector.get_conflict_summary()
        assert "Conflict Detection Summary" in summary

    def test_prompt_conflicts(self, detector: ConflictDetector) -> None:
        analyses = [
            DotfileAnalysis(
                path="/test/.zshrc",
                file_type="zsh",
                dependencies=[
                    Dependency(name="starship", dependency_type="package"),
                ],
                environment_variables={
                    "PROMPT": "%n@%m %~ %# ",
                },
                aliases={},
                functions=[],
            ),
            DotfileAnalysis(
                path="/test/.p10k.zsh",
                file_type="zsh",
                dependencies=[
                    Dependency(name="powerlevel10k", dependency_type="plugin"),
                ],
                environment_variables={
                    "PROMPT": "${P9K_CONTENT}",
                },
                aliases={},
                functions=[],
            ),
        ]
        conflicts = detector.detect_conflicts(analyses)
        prompt_conflicts = [c for c in conflicts if "PROMPT" in c.affected_variable]
        assert len(prompt_conflicts) > 0
