"""Environment variable resolver for dotfiles."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from dotsync.analyzer import DotfileAnalyzer


class EnvVarResolver:
    """Resolves and manages environment variables from dotfiles."""

    # Common environment variable patterns
    PATH_EXPANSION = re.compile(r"\$HOME|\$USER|\$SHELL|~")
    VAR_REFERENCE = re.compile(r"\$\{?(\w+)\}?")

    def __init__(self, dotfiles_path: str | Path):
        self.dotfiles_path = Path(dotfiles_path)
        self.env_vars: dict[str, dict[str, Any]] = {}

    def collect_env_vars(self) -> dict[str, dict[str, Any]]:
        """Collect all environment variable definitions from dotfiles."""
        analyzer = DotfileAnalyzer(self.dotfiles_path)
        analyses = analyzer.analyze_all()

        self.env_vars = {}

        for analysis in analyses:
            for var_name, var_value in analysis.environment_variables.items():
                if var_name not in self.env_vars:
                    self.env_vars[var_name] = {
                        "value": var_value,
                        "source": analysis.path,
                        "resolved_value": self._resolve_value(var_value),
                        "references": self._find_references(var_value),
                        "is_path": self._is_path_var(var_name),
                    }
                else:
                    # Track multiple definitions
                    existing = self.env_vars[var_name]
                    if not isinstance(existing.get("sources"), list):
                        existing["sources"] = [existing["source"]]
                        existing["values"] = [existing["value"]]
                    existing["sources"].append(analysis.path)
                    existing["values"].append(var_value)

        return self.env_vars

    def _resolve_value(self, value: str) -> str:
        """Resolve environment variable references in a value."""
        resolved = value

        # Expand ~ to HOME
        resolved = resolved.replace("~", os.path.expanduser("~"))

        # Resolve $HOME
        resolved = resolved.replace("$HOME", os.path.expanduser("~"))

        # Resolve $USER
        resolved = resolved.replace("$USER", os.environ.get("USER", ""))

        # Resolve $SHELL
        resolved = resolved.replace("$SHELL", os.environ.get("SHELL", ""))

        return resolved

    def _find_references(self, value: str) -> list[str]:
        """Find all variable references in a value."""
        return self.VAR_REFERENCE.findall(value)

    def _is_path_var(self, name: str) -> bool:
        """Check if a variable is likely a path variable."""
        path_indicators = ["PATH", "DIR", "HOME", "ROOT", "BASE", "FILE"]
        return any(indicator in name.upper() for indicator in path_indicators)

    def get_dependency_order(self) -> list[str]:
        """Get environment variables in dependency order."""
        # Build dependency graph
        deps: dict[str, set[str]] = {}
        for var_name, var_info in self.env_vars.items():
            refs = set(var_info.get("references", []))
            # Only consider refs that are also defined env vars
            deps[var_name] = refs & set(self.env_vars.keys())

        # Topological sort
        ordered = []
        visited = set()

        def visit(var: str) -> None:
            if var in visited:
                return
            visited.add(var)
            for dep in deps.get(var, set()):
                visit(dep)
            ordered.append(var)

        for var in self.env_vars:
            visit(var)

        return ordered

    def generate_export_script(self, shell: str = "bash") -> str:
        """Generate a script to export all environment variables."""
        lines = [f"#!/usr/bin/env {shell}", "# Auto-generated environment variable exports", ""]

        ordered = self.get_dependency_order()

        for var_name in ordered:
            var_info = self.env_vars[var_name]
            value = var_info["value"]
            source = var_info["source"]

            lines.append(f"# From: {source}")
            lines.append(f'export {var_name}="{value}"')
            lines.append("")

        return "\n".join(lines)

    def check_circular_deps(self) -> list[list[str]]:
        """Check for circular dependencies between environment variables."""
        cycles = []
        deps: dict[str, set[str]] = {}

        for var_name, var_info in self.env_vars.items():
            refs = set(var_info.get("references", []))
            deps[var_name] = refs & set(self.env_vars.keys())

        # Simple cycle detection
        for var in deps:
            visited = set()
            current = var
            while current in deps:
                if current in visited:
                    cycle_start = list(visited).index(current)
                    cycle = list(visited)[cycle_start:] + [current]
                    if cycle not in cycles:
                        cycles.append(cycle)
                    break
                visited.add(current)
                # Move to first dependency
                if deps[current]:
                    current = next(iter(deps[current]))
                else:
                    break

        return cycles

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of environment variables."""
        return {
            "total_vars": len(self.env_vars),
            "path_vars": sum(1 for v in self.env_vars.values() if v.get("is_path")),
            "circular_deps": len(self.check_circular_deps()),
            "vars": {
                name: {
                    "value": info["value"],
                    "source": Path(info["source"]).name,
                    "resolved": info["resolved_value"],
                }
                for name, info in self.env_vars.items()
            },
        }
