"""Tests for the dependency graph module."""

from pathlib import Path

import pytest

from dotsync.analyzer import DotfileAnalyzer
from dotsync.dependency_graph import DependencyGraphBuilder
from dotsync.models import DependencyGraph


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def analyses(fixtures_dir: Path) -> list:
    analyzer = DotfileAnalyzer(fixtures_dir)
    return analyzer.analyze_all()


@pytest.fixture
def graph_builder() -> DependencyGraphBuilder:
    return DependencyGraphBuilder()


@pytest.fixture
def dep_graph(analyses: list, graph_builder: DependencyGraphBuilder) -> DependencyGraph:
    return graph_builder.build(analyses)


class TestDependencyGraphBuilder:
    """Tests for DependencyGraphBuilder."""

    def test_build_graph(self, dep_graph: DependencyGraph) -> None:
        assert len(dep_graph.nodes) > 0
        assert len(dep_graph.edges) > 0

    def test_graph_has_dotfile_nodes(self, dep_graph: DependencyGraph) -> None:
        node_names = [n.name for n in dep_graph.nodes]
        assert any(".zshrc" in name for name in node_names)

    def test_graph_has_dependency_nodes(self, dep_graph: DependencyGraph) -> None:
        node_names = [n.name for n in dep_graph.nodes]
        # Should have some common dependencies
        assert any("starship" in name for name in node_names)

    def test_to_mermaid(self, dep_graph: DependencyGraph) -> None:
        mermaid = dep_graph.to_mermaid()
        assert "graph TD" in mermaid

    def test_root_nodes(self, graph_builder: DependencyGraphBuilder, analyses: list) -> None:
        graph_builder.build(analyses)
        roots = graph_builder.get_root_nodes()
        assert len(roots) > 0

    def test_leaf_nodes(self, graph_builder: DependencyGraphBuilder, analyses: list) -> None:
        graph_builder.build(analyses)
        leaves = graph_builder.get_leaf_nodes()
        assert len(leaves) > 0

    def test_topological_order(self, graph_builder: DependencyGraphBuilder, analyses: list) -> None:
        graph_builder.build(analyses)
        order = graph_builder.get_topological_order()
        # Should return a valid ordering (may be empty if cycles exist)
        assert isinstance(order, list)

    def test_get_dependencies(self, graph_builder: DependencyGraphBuilder, analyses: list) -> None:
        graph_builder.build(analyses)
        # Get dependencies for zshrc
        zshrc_analyses = next((a for a in analyses if ".zshrc" in a.path), None)
        if zshrc_analyses:
            deps = graph_builder.get_dependencies(zshrc_analyses.path)
            assert isinstance(deps, list)

    def test_get_dependents(self, graph_builder: DependencyGraphBuilder, analyses: list) -> None:
        graph_builder.build(analyses)
        # Get dependents for starship
        dependents = graph_builder.get_dependents("starship")
        assert isinstance(dependents, list)
