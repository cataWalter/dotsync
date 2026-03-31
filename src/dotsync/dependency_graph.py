"""Dependency graph builder using networkx."""

from __future__ import annotations

import networkx as nx

from dotsync.models import (
    DependencyEdge,
    DependencyGraph,
    DependencyNode,
    DotfileAnalysis,
)


class DependencyGraphBuilder:
    """Builds and analyzes dependency graphs from dotfile analyses."""

    def __init__(self):
        self.graph = nx.DiGraph()
        self._nodes: dict[str, DependencyNode] = {}
        self._edges: list[DependencyEdge] = []

    def build(self, analyses: list[DotfileAnalysis]) -> DependencyGraph:
        """Build a dependency graph from a list of dotfile analyses."""
        self.graph.clear()
        self._nodes.clear()
        self._edges.clear()

        # Add dotfile nodes
        for analysis in analyses:
            node_id = self._make_node_id(analysis.path)
            node = DependencyNode(
                name=analysis.path,
                node_type=analysis.file_type,
                source_file=analysis.path,
                properties={
                    "dependencies_count": len(analysis.dependencies),
                    "aliases_count": len(analysis.aliases),
                    "functions_count": len(analysis.functions),
                },
            )
            self._nodes[node_id] = node
            self.graph.add_node(node_id, **node.model_dump())

        # Add dependency nodes and edges
        for analysis in analyses:
            source_node_id = self._make_node_id(analysis.path)
            for dep in analysis.dependencies:
                dep_node_id = self._make_node_id(dep.name)

                # Add dependency node if not exists
                if dep_node_id not in self._nodes:
                    dep_node = DependencyNode(
                        name=dep.name,
                        node_type=dep.dependency_type,
                        source_file=dep.source_file,
                        properties={
                            "required": dep.required,
                            "version": dep.version,
                        },
                    )
                    self._nodes[dep_node_id] = dep_node
                    self.graph.add_node(dep_node_id, **dep_node.model_dump())

                # Add edge
                edge = DependencyEdge(
                    source=analysis.path,
                    target=dep.name,
                    edge_type="requires",
                )
                self._edges.append(edge)
                self.graph.add_edge(source_node_id, dep_node_id, edge_type=edge.edge_type)

        # Add implicit edges between dependencies (e.g., plugin -> plugin manager)
        self._add_implicit_edges(analyses)

        return DependencyGraph(
            nodes=list(self._nodes.values()),
            edges=self._edges,
        )

    def _add_implicit_edges(self, analyses: list[DotfileAnalysis]) -> None:
        """Add implicit edges based on known relationships."""
        # Known plugin manager relationships
        plugin_managers = {
            "zplug": ["zsh"],
            "zinit": ["zsh"],
            "antibody": ["zsh"],
            "antidote": ["zsh"],
            "oh-my-zsh": ["zsh"],
            "vim-plug": ["vim"],
            "packer.nvim": ["nvim"],
            "lazy.nvim": ["nvim"],
        }

        for manager, targets in plugin_managers.items():
            manager_id = self._make_node_id(manager)
            if manager_id in self._nodes:
                for target in targets:
                    target_id = self._make_node_id(target)
                    if target_id in self._nodes:
                        edge = DependencyEdge(
                            source=manager,
                            target=target,
                            edge_type="requires",
                        )
                        self._edges.append(edge)
                        self.graph.add_edge(manager_id, target_id, edge_type=edge.edge_type)

    def _make_node_id(self, name: str) -> str:
        """Create a valid node ID from a name."""
        return name.replace(".", "_").replace("-", "_").replace("/", "_").replace(" ", "_")

    def get_root_nodes(self) -> list[str]:
        """Get nodes with no incoming edges (root dotfiles)."""
        return [n for n, d in self.graph.in_degree() if d == 0]

    def get_leaf_nodes(self) -> list[str]:
        """Get nodes with no outgoing edges (leaf dependencies)."""
        return [n for n, d in self.graph.out_degree() if d == 0]

    def get_critical_path(self) -> list[str]:
        """Get the longest path in the dependency graph."""
        try:
            return list(nx.dag_longest_path(self.graph))
        except nx.NetworkXError:
            return []

    def has_cycles(self) -> bool:
        """Check if the graph has any cycles."""
        try:
            return not nx.is_directed_acyclic_graph(self.graph)
        except nx.NetworkXError:
            return True

    def get_topological_order(self) -> list[str]:
        """Get nodes in topological order (installation order)."""
        try:
            return list(nx.topological_sort(self.graph))
        except nx.NetworkXError:
            return []

    def get_dependents(self, node_name: str) -> list[str]:
        """Get all nodes that depend on the given node."""
        node_id = self._make_node_id(node_name)
        if node_id in self.graph:
            return list(nx.ancestors(self.graph, node_id))
        return []

    def get_dependencies(self, node_name: str) -> list[str]:
        """Get all dependencies of the given node."""
        node_id = self._make_node_id(node_name)
        if node_id in self.graph:
            return list(nx.descendants(self.graph, node_id))
        return []

    def to_mermaid(self) -> str:
        """Export the graph as a Mermaid diagram."""
        lines = ["graph TD"]

        # Add nodes with styling
        for node_id, node in self._nodes.items():
            lines.append(f'    {node_id}["{node.name}"]:::{node.node_type}')

        # Add edges
        for edge in self._edges:
            source_id = self._make_node_id(edge.source)
            target_id = self._make_node_id(edge.target)
            lines.append(f"    {source_id} -->|{edge.edge_type}| {target_id}")

        # Add class definitions
        lines.append("")
        lines.append("    classDef bash fill:#4eaa25,stroke:#333")
        lines.append("    classDef zsh fill:#4eaa25,stroke:#333")
        lines.append("    classDef sh fill:#89e051,stroke:#333")
        lines.append("    classDef vim fill:#019733,stroke:#333")
        lines.append("    classDef tmux fill:#1bb91f,stroke:#333")
        lines.append("    classDef package fill:#3498db,stroke:#333")
        lines.append("    classDef plugin fill:#9b59b6,stroke:#333")
        lines.append("    classDef command fill:#e67e22,stroke:#333")

        return "\n".join(lines)

    def get_installation_order(self) -> list[str]:
        """Get the recommended installation order for dependencies."""
        order = self.get_topological_order()
        # Filter to only include leaf nodes (actual packages/commands)
        return [
            n
            for n in order
            if self._nodes.get(n, DependencyNode(name="", node_type="")).node_type
            in ("package", "command", "plugin")
        ]
