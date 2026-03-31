"""Tests for the models module."""


from dotsync.models import (
    CompatibilityIssue,
    Conflict,
    Dependency,
    DependencyEdge,
    DependencyGraph,
    DependencyNode,
    DotfileAnalysis,
    MigrationPlan,
    MigrationStep,
    PlatformDefinition,
    Severity,
)


class TestModels:
    """Tests for Pydantic models."""

    def test_severity_enum(self) -> None:
        assert Severity.INFO == "info"
        assert Severity.WARNING == "warning"
        assert Severity.ERROR == "error"
        assert Severity.CRITICAL == "critical"

    def test_dependency_model(self) -> None:
        dep = Dependency(name="starship", dependency_type="package")
        assert dep.name == "starship"
        assert dep.required is True

    def test_dotfile_analysis_model(self) -> None:
        analysis = DotfileAnalysis(path="/test/.zshrc", file_type="zsh")
        assert analysis.path == "/test/.zshrc"
        assert analysis.file_type == "zsh"
        assert len(analysis.dependencies) == 0

    def test_platform_definition_model(self) -> None:
        platform = PlatformDefinition(
            name="macos",
            package_manager="brew",
        )
        assert platform.name == "macos"
        assert platform.package_manager == "brew"

    def test_compatibility_issue_model(self) -> None:
        issue = CompatibilityIssue(
            severity=Severity.ERROR,
            message="Test issue",
        )
        assert issue.severity == Severity.ERROR
        assert issue.message == "Test issue"

    def test_conflict_model(self) -> None:
        conflict = Conflict(
            severity=Severity.WARNING,
            description="Test conflict",
        )
        assert conflict.severity == Severity.WARNING
        assert conflict.description == "Test conflict"

    def test_migration_step_model(self) -> None:
        step = MigrationStep(
            order=1,
            action="install",
            description="Install package",
            command="brew install pkg",
        )
        assert step.order == 1
        assert step.action == "install"

    def test_migration_plan_model(self) -> None:
        plan = MigrationPlan(
            source_platform="macos",
            target_platform="linux-ubuntu",
        )
        assert plan.source_platform == "macos"
        assert plan.target_platform == "linux-ubuntu"
        assert plan.backup_required is True

    def test_dependency_node_model(self) -> None:
        node = DependencyNode(
            name="starship",
            node_type="package",
        )
        assert node.name == "starship"
        assert node.node_type == "package"

    def test_dependency_edge_model(self) -> None:
        edge = DependencyEdge(
            source=".zshrc",
            target="starship",
        )
        assert edge.source == ".zshrc"
        assert edge.target == "starship"
        assert edge.edge_type == "requires"

    def test_dependency_graph_to_mermaid(self) -> None:
        graph = DependencyGraph(
            nodes=[
                DependencyNode(name=".zshrc", node_type="zsh"),
                DependencyNode(name="starship", node_type="package"),
            ],
            edges=[
                DependencyEdge(source=".zshrc", target="starship"),
            ],
        )
        mermaid = graph.to_mermaid()
        assert "graph TD" in mermaid
        assert ".zshrc" in mermaid
        assert "starship" in mermaid
