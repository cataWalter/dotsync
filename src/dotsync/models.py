"""Pydantic data models for DotSync."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity levels for compatibility issues and conflicts."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class PlatformType(str, Enum):
    """Supported platform types."""

    MACOS = "macos"
    LINUX_UBUNTU = "linux-ubuntu"
    LINUX_ARCH = "linux-arch"
    LINUX_FEDORA = "linux-fedora"
    NIXOS = "nixos"
    WINDOWS_WSL = "windows-wsl"


class Dependency(BaseModel):
    """Represents a dependency extracted from a dotfile."""

    name: str
    version: str | None = None
    required: bool = True
    source_file: str = ""
    line_number: int | None = None
    dependency_type: str = "package"  # package, command, plugin, etc.


class DotfileAnalysis(BaseModel):
    """Analysis result for a single dotfile."""

    path: str
    file_type: str
    dependencies: list[Dependency] = Field(default_factory=list)
    environment_variables: dict[str, str] = Field(default_factory=dict)
    aliases: dict[str, str] = Field(default_factory=dict)
    functions: list[str] = Field(default_factory=list)
    raw_content: str = ""
    parse_errors: list[str] = Field(default_factory=list)


class PlatformDefinition(BaseModel):
    """Platform-specific configuration and capabilities."""

    name: str
    package_manager: str
    shell_default: str = "/bin/bash"
    config_paths: dict[str, str] = Field(default_factory=dict)
    package_map: dict[str, str] = Field(default_factory=dict)
    incompatible_tools: list[str] = Field(default_factory=list)
    supported_shells: list[str] = Field(default_factory=lambda: ["bash", "zsh"])
    os_family: str = "linux"  # linux, darwin, windows
    arch_support: list[str] = Field(default_factory=lambda: ["x86_64", "arm64"])


class CompatibilityIssue(BaseModel):
    """Represents a compatibility issue between source and target platform."""

    severity: Severity
    message: str
    source: str = ""
    target: str = ""
    suggestion: str = ""
    affected_files: list[str] = Field(default_factory=list)


class Conflict(BaseModel):
    """Represents a configuration conflict between tools."""

    severity: Severity
    description: str
    conflicting_items: list[str] = Field(default_factory=list)
    affected_variable: str = ""
    resolution: str = ""


class MigrationStep(BaseModel):
    """A single step in a migration script."""

    order: int
    action: str  # install, copy, modify, create, remove
    description: str
    command: str
    condition: str = ""  # Shell condition for this step
    rollback_command: str = ""
    platform: str = ""  # Empty means all platforms


class MigrationPlan(BaseModel):
    """Complete migration plan from source to target platform."""

    source_platform: str
    target_platform: str
    steps: list[MigrationStep] = Field(default_factory=list)
    issues: list[CompatibilityIssue] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    estimated_time: str = ""
    backup_required: bool = True


class DependencyNode(BaseModel):
    """A node in the dependency graph."""

    name: str
    node_type: str  # dotfile, package, command, plugin
    source_file: str = ""
    properties: dict[str, Any] = Field(default_factory=dict)


class DependencyEdge(BaseModel):
    """An edge in the dependency graph."""

    source: str
    target: str
    edge_type: str = "requires"  # requires, optional, conflicts


class DependencyGraph(BaseModel):
    """Complete dependency graph representation."""

    nodes: list[DependencyNode] = Field(default_factory=list)
    edges: list[DependencyEdge] = Field(default_factory=list)

    def to_mermaid(self) -> str:
        """Convert the dependency graph to Mermaid format."""
        lines = ["graph TD"]

        # Add nodes
        for node in self.nodes:
            node_id = node.name.replace(".", "_").replace("-", "_").replace("/", "_")
            label = f"{node.name} ({node.node_type})"
            lines.append(f'    {node_id}["{label}"]')

        # Add edges
        for edge in self.edges:
            source_id = edge.source.replace(".", "_").replace("-", "_").replace("/", "_")
            target_id = edge.target.replace(".", "_").replace("-", "_").replace("/", "_")
            lines.append(f"    {source_id} -->|{edge.edge_type}| {target_id}")

        return "\n".join(lines)


class AnalysisReport(BaseModel):
    """Complete analysis report for a dotfiles directory."""

    source_path: str
    analyzed_files: list[DotfileAnalysis] = Field(default_factory=list)
    dependency_graph: DependencyGraph = Field(default_factory=DependencyGraph)
    total_dependencies: int = 0
    total_issues: int = 0
    platform_compatibility: dict[str, list[CompatibilityIssue]] = Field(default_factory=dict)
    conflicts: list[Conflict] = Field(default_factory=list)
