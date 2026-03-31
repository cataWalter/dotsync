"""Conflict detection engine for dotfile configurations."""

from __future__ import annotations

import re
from collections import defaultdict

from dotsync.models import Conflict, DotfileAnalysis, Severity

# Known conflict patterns
CONFLICT_PATTERNS = {
    # Environment variable conflicts
    "path_override": {
        "description": "Multiple tools modifying PATH",
        "pattern": re.compile(r"export\s+PATH\s*="),
        "severity": Severity.WARNING,
    },
    "editor_override": {
        "description": "Multiple EDITOR definitions",
        "pattern": re.compile(r"export\s+EDITOR\s*="),
        "severity": Severity.INFO,
    },
    "terminal_override": {
        "description": "Multiple TERMINAL definitions",
        "pattern": re.compile(r"export\s+TERM\s*="),
        "severity": Severity.INFO,
    },
    # Shell option conflicts
    "shell_options": {
        "description": "Conflicting shell options (set -o / setopt)",
        "pattern": re.compile(r"(?:set\s+-[oO]|setopt|unsetopt)\s+(\w+)"),
        "severity": Severity.WARNING,
    },
    # Key binding conflicts
    "key_bindings": {
        "description": "Conflicting key bindings",
        "pattern": re.compile(r"bindkey\s+"),
        "severity": Severity.WARNING,
    },
    # Prompt conflicts
    "prompt_config": {
        "description": "Multiple prompt configurations",
        "pattern": re.compile(r"(?:PROMPT|PS1|RPROMPT|RPS1)\s*="),
        "severity": Severity.WARNING,
    },
}

# Known tool conflicts (tools that often conflict with each other)
KNOWN_TOOL_CONFLICTS = [
    {
        "tools": ["oh-my-zsh", "prezto", "zsh-autosuggestions"],
        "description": "Oh My Zsh and Prezto both provide framework features that may conflict",
        "affected_variable": "fpath",
        "resolution": "Choose one framework (oh-my-zsh or prezto) and disable the other",
    },
    {
        "tools": ["starship", "powerlevel10k", "pure"],
        "description": "Multiple prompt themes detected",
        "affected_variable": "PROMPT",
        "resolution": "Choose one prompt theme and remove or disable others",
    },
    {
        "tools": ["fzf", "fzf-tab"],
        "description": "FZF and fzf-tab may have overlapping key bindings",
        "affected_variable": "ZLE_WIDGETS",
        "resolution": "Review key bindings and disable overlapping widgets",
    },
    {
        "tools": ["z", "zoxide", "autojump"],
        "description": "Multiple directory jump tools detected",
        "affected_variable": "PATH",
        "resolution": "Choose one directory jump tool (z, zoxide, or autojump)",
    },
    {
        "tools": ["exa", "eza", "lsd"],
        "description": "Multiple ls replacements detected",
        "affected_variable": "aliases",
        "resolution": "Choose one ls replacement and update aliases accordingly",
    },
    {
        "tools": ["vim", "neovim", "nvim"],
        "description": "Both Vim and Neovim configurations detected",
        "affected_variable": "EDITOR",
        "resolution": "Set EDITOR to your preferred editor and consider removing unused configs",
    },
]


class ConflictDetector:
    """Detects configuration conflicts between dotfiles."""

    def __init__(self):
        self.conflicts: list[Conflict] = []

    def detect_conflicts(self, analyses: list[DotfileAnalysis]) -> list[Conflict]:
        """Detect all types of conflicts in the analyzed dotfiles."""
        self.conflicts = []

        # Check for environment variable conflicts
        self._detect_env_conflicts(analyses)

        # Check for alias conflicts
        self._detect_alias_conflicts(analyses)

        # Check for function name conflicts
        self._detect_function_conflicts(analyses)

        # Check for known tool conflicts
        self._detect_tool_conflicts(analyses)

        # Check for shell option conflicts
        self._detect_shell_option_conflicts(analyses)

        # Check for prompt conflicts
        self._detect_prompt_conflicts(analyses)

        return self.conflicts

    def _detect_env_conflicts(self, analyses: list[DotfileAnalysis]) -> None:
        """Detect conflicting environment variable definitions."""
        env_sources: dict[str, list[tuple[str, str]]] = defaultdict(list)

        for analysis in analyses:
            for var_name, var_value in analysis.environment_variables.items():
                env_sources[var_name].append((analysis.path, var_value))

        for var_name, sources in env_sources.items():
            if len(sources) > 1:
                # Check if values are actually different
                values = set(v for _, v in sources)
                if len(values) > 1:
                    self.conflicts.append(
                        Conflict(
                            severity=Severity.WARNING,
                            description=f"Environment variable '{var_name}' has conflicting definitions",
                            conflicting_items=[f"{path}: {value}" for path, value in sources],
                            affected_variable=var_name,
                            resolution=f"Consolidate '{var_name}' definitions into a single file",
                        )
                    )

    def _detect_alias_conflicts(self, analyses: list[DotfileAnalysis]) -> None:
        """Detect conflicting alias definitions."""
        alias_sources: dict[str, list[tuple[str, str]]] = defaultdict(list)

        for analysis in analyses:
            for alias_name, alias_value in analysis.aliases.items():
                alias_sources[alias_name].append((analysis.path, alias_value))

        for alias_name, sources in alias_sources.items():
            if len(sources) > 1:
                values = set(v for _, v in sources)
                if len(values) > 1:
                    self.conflicts.append(
                        Conflict(
                            severity=Severity.WARNING,
                            description=f"Alias '{alias_name}' has conflicting definitions",
                            conflicting_items=[f"{path}: {value}" for path, value in sources],
                            affected_variable=alias_name,
                            resolution=f"Consolidate '{alias_name}' alias into a single definition",
                        )
                    )

    def _detect_function_conflicts(self, analyses: list[DotfileAnalysis]) -> None:
        """Detect conflicting function definitions."""
        func_sources: dict[str, list[str]] = defaultdict(list)

        for analysis in analyses:
            for func_name in analysis.functions:
                func_sources[func_name].append(analysis.path)

        for func_name, sources in func_sources.items():
            if len(sources) > 1:
                self.conflicts.append(
                    Conflict(
                        severity=Severity.ERROR,
                        description=f"Function '{func_name}' is defined in multiple files",
                        conflicting_items=sources,
                        affected_variable=func_name,
                        resolution=f"Keep only one definition of '{func_name}' or rename to avoid conflicts",
                    )
                )

    def _detect_tool_conflicts(self, analyses: list[DotfileAnalysis]) -> None:
        """Detect known tool conflicts."""
        # Collect all dependencies
        all_deps: set[str] = set()
        dep_sources: dict[str, list[str]] = defaultdict(list)

        for analysis in analyses:
            for dep in analysis.dependencies:
                all_deps.add(dep.name)
                dep_sources[dep.name].append(analysis.path)

        # Check against known conflicts
        for conflict_info in KNOWN_TOOL_CONFLICTS:
            conflicting_tools = [t for t in conflict_info["tools"] if t in all_deps]
            if len(conflicting_tools) > 1:
                self.conflicts.append(
                    Conflict(
                        severity=Severity.WARNING,
                        description=conflict_info["description"],
                        conflicting_items=conflicting_tools,
                        affected_variable=conflict_info["affected_variable"],
                        resolution=conflict_info["resolution"],
                    )
                )

    def _detect_shell_option_conflicts(self, analyses: list[DotfileAnalysis]) -> None:
        """Detect conflicting shell options."""
        options: dict[str, list[tuple[str, bool, str]]] = defaultdict(list)

        for analysis in analyses:
            for line in analysis.raw_content.split("\n"):
                # Check setopt/unsetopt
                match = re.match(r"\s*(setopt|unsetopt)\s+(\w+)", line)
                if match:
                    cmd, option = match.groups()
                    enabled = cmd == "setopt"
                    options[option].append((analysis.path, enabled, line.strip()))

                # Check set -o / set +o
                match = re.match(r"\s*set\s+([+-])o\s+(\w+)", line)
                if match:
                    sign, option = match.groups()
                    enabled = sign == "+"
                    options[option].append((analysis.path, enabled, line.strip()))

        for option, sources in options.items():
            if len(sources) > 1:
                # Check for conflicting enable/disable
                enabled_values = set(e for _, e, _ in sources)
                if len(enabled_values) > 1:
                    self.conflicts.append(
                        Conflict(
                            severity=Severity.WARNING,
                            description=f"Shell option '{option}' has conflicting settings",
                            conflicting_items=[f"{path}: {line}" for path, _, line in sources],
                            affected_variable=option,
                            resolution=f"Consolidate '{option}' settings into a single location",
                        )
                    )

    def _detect_prompt_conflicts(self, analyses: list[DotfileAnalysis]) -> None:
        """Detect conflicting prompt configurations."""
        prompt_sources: dict[str, list[tuple[str, str]]] = defaultdict(list)

        prompt_vars = ["PROMPT", "PS1", "RPROMPT", "RPS1", "SPROMPT"]

        for analysis in analyses:
            for var_name in prompt_vars:
                if var_name in analysis.environment_variables:
                    prompt_sources[var_name].append(
                        (analysis.path, analysis.environment_variables[var_name])
                    )

        for var_name, sources in prompt_sources.items():
            if len(sources) > 1:
                values = set(v for _, v in sources)
                if len(values) > 1:
                    self.conflicts.append(
                        Conflict(
                            severity=Severity.WARNING,
                            description=f"Prompt variable '{var_name}' has conflicting definitions",
                            conflicting_items=[
                                f"{path}: {value[:50]}..." for path, value in sources
                            ],
                            affected_variable=var_name,
                            resolution=(
                                "Use a single prompt configuration "
                                "(consider starship for cross-shell compatibility)"
                            ),
                        )
                    )

    def get_conflict_summary(self) -> str:
        """Get a human-readable summary of all conflicts."""
        if not self.conflicts:
            return "No conflicts detected."

        lines = ["Conflict Detection Summary", "=" * 40, ""]

        for i, conflict in enumerate(self.conflicts, 1):
            lines.append(f"{i}. [{conflict.severity.value.upper()}] {conflict.description}")
            lines.append(f"   Affected: {conflict.affected_variable}")
            lines.append(f"   Sources: {', '.join(conflict.conflicting_items)}")
            lines.append(f"   Resolution: {conflict.resolution}")
            lines.append("")

        return "\n".join(lines)
