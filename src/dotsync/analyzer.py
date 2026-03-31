"""AST-based parsing of dotfiles for dependency extraction."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

from dotsync.models import Dependency, DotfileAnalysis


# Common patterns for shell script analysis
SHELL_PATTERNS = {
    "source_command": re.compile(r"^\s*(?:source|\.)\s+(.+)$", re.MULTILINE),
    "export_command": re.compile(r"^\s*export\s+(\w+)=(.+)$", re.MULTILINE),
    "alias_command": re.compile(r"^\s*alias\s+(\w+)=[\"'](.+?)[\"']\s*$", re.MULTILINE),
    "function_definition": re.compile(r"^\s*(?:function\s+)?(\w+)\s*(?:\(\))?\s*\{", re.MULTILINE),
    "command_check": re.compile(r"^\s*(?:command\s+-v|which|type)\s+(\w+)", re.MULTILINE),
    "brew_install": re.compile(r"^\s*brew\s+(?:install|tap)\s+(.+)$", re.MULTILINE),
    "apt_install": re.compile(r"^\s*(?:apt|apt-get)\s+install\s+(.+)$", re.MULTILINE),
    "pacman_install": re.compile(r"^\s*pacman\s+-S\s+(.+)$", re.MULTILINE),
    "dnf_install": re.compile(r"^\s*(?:dnf|yum)\s+install\s+(.+)$", re.MULTILINE),
    "npm_install": re.compile(r"^\s*npm\s+install\s+(?:-g\s+)?(.+)$", re.MULTILINE),
    "pip_install": re.compile(r"^\s*pip3?\s+install\s+(.+)$", re.MULTILINE),
    "plugin_manager": re.compile(
        r"(?:zplug|zinit|antibody|antidote|oh-my-zsh)\s+(?:load|plugin)\s+(\S+)", re.MULTILINE
    ),
}

# File type detection
FILE_TYPE_MAP = {
    ".zshrc": "zsh",
    ".bashrc": "bash",
    ".bash_profile": "bash",
    ".profile": "sh",
    ".gitconfig": "gitconfig",
    ".vimrc": "vim",
    ".nvimrc": "vim",
    "init.vim": "vim",
    "init.lua": "lua",
    ".tmux.conf": "tmux",
    ".xinitrc": "sh",
    ".xprofile": "sh",
}

# File extension to type map
EXTENSION_TYPE_MAP = {
    ".toml": "toml",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".sh": "sh",
    ".zsh": "zsh",
    ".bash": "bash",
    ".conf": "config",
    ".cfg": "config",
}


class DotfileAnalyzer:
    """Analyzes dotfiles and extracts dependencies using pattern matching and AST parsing."""

    def __init__(self, dotfiles_path: str | Path):
        self.dotfiles_path = Path(dotfiles_path)
        self.analyses: list[DotfileAnalysis] = []

    def analyze_all(self) -> list[DotfileAnalysis]:
        """Analyze all dotfiles in the specified directory."""
        if not self.dotfiles_path.exists():
            raise FileNotFoundError(f"Dotfiles directory not found: {self.dotfiles_path}")

        self.analyses = []
        for file_path in self._find_dotfiles():
            analysis = self._analyze_file(file_path)
            self.analyses.append(analysis)

        return self.analyses

    def _find_dotfiles(self) -> list[Path]:
        """Find all dotfiles in the directory."""
        dotfiles = []

        # Common dotfile patterns
        patterns = [
            ".zshrc", ".bashrc", ".bash_profile", ".profile",
            ".gitconfig", ".vimrc", ".nvimrc", ".tmux.conf",
            ".xinitrc", ".xprofile", ".inputrc", ".wgetrc",
            ".curlrc", ".editorconfig",
        ]

        # Check for files directly in the directory
        for pattern in patterns:
            file_path = self.dotfiles_path / pattern
            if file_path.is_file():
                dotfiles.append(file_path)

        # Check .config directory
        config_dir = self.dotfiles_path / ".config"
        if config_dir.is_dir():
            for file_path in config_dir.rglob("*"):
                if file_path.is_file():
                    dotfiles.append(file_path)

        # Check for any hidden files
        for file_path in self.dotfiles_path.glob(".*"):
            if file_path.is_file() and file_path not in dotfiles:
                dotfiles.append(file_path)

        return dotfiles

    def _analyze_file(self, file_path: Path) -> DotfileAnalysis:
        """Analyze a single dotfile."""
        file_type = self._detect_file_type(file_path)
        content = file_path.read_text(encoding="utf-8", errors="replace")

        analysis = DotfileAnalysis(
            path=str(file_path),
            file_type=file_type,
            raw_content=content,
        )

        # Parse based on file type
        if file_type in ("bash", "zsh", "sh"):
            self._parse_shell_script(content, analysis)
        elif file_type == "gitconfig":
            self._parse_gitconfig(content, analysis)
        elif file_type == "toml":
            self._parse_toml(content, analysis)
        elif file_type == "json":
            self._parse_json(content, analysis)
        elif file_type == "yaml":
            self._parse_yaml_file(content, analysis)
        elif file_type == "vim":
            self._parse_vimrc(content, analysis)
        elif file_type == "tmux":
            self._parse_tmux_conf(content, analysis)
        else:
            # Try shell script parsing as fallback
            self._parse_shell_script(content, analysis)

        return analysis

    def _detect_file_type(self, file_path: Path) -> str:
        """Detect the file type based on name and extension."""
        name = file_path.name

        # Check exact name matches
        if name in FILE_TYPE_MAP:
            return FILE_TYPE_MAP[name]

        # Check extension
        ext = file_path.suffix.lower()
        if ext in EXTENSION_TYPE_MAP:
            return EXTENSION_TYPE_MAP[ext]

        # Check for known patterns
        if "vim" in name.lower():
            return "vim"
        if "tmux" in name.lower():
            return "tmux"
        if "git" in name.lower():
            return "gitconfig"

        return "unknown"

    def _parse_shell_script(self, content: str, analysis: DotfileAnalysis) -> None:
        """Parse shell script files (bash, zsh, sh)."""
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Skip comments and empty lines
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Extract source/. commands
            match = SHELL_PATTERNS["source_command"].match(line)
            if match:
                source_path = match.group(1).strip().strip('"').strip("'")
                analysis.dependencies.append(
                    Dependency(
                        name=source_path,
                        source_file=analysis.path,
                        line_number=line_num,
                        dependency_type="source",
                    )
                )

            # Extract exports
            match = SHELL_PATTERNS["export_command"].match(line)
            if match:
                var_name = match.group(1)
                var_value = match.group(2).strip().strip('"').strip("'")
                analysis.environment_variables[var_name] = var_value

            # Extract aliases
            match = SHELL_PATTERNS["alias_command"].match(line)
            if match:
                alias_name = match.group(1)
                alias_value = match.group(2)
                analysis.aliases[alias_name] = alias_value

            # Extract function definitions
            match = SHELL_PATTERNS["function_definition"].match(line)
            if match:
                analysis.functions.append(match.group(1))

            # Extract command checks (which/type/command -v)
            match = SHELL_PATTERNS["command_check"].match(line)
            if match:
                cmd = match.group(1)
                analysis.dependencies.append(
                    Dependency(
                        name=cmd,
                        source_file=analysis.path,
                        line_number=line_num,
                        dependency_type="command",
                    )
                )

            # Extract package manager commands
            for pattern_name, pattern in SHELL_PATTERNS.items():
                if pattern_name in ("source_command", "export_command", "alias_command",
                                    "function_definition", "command_check"):
                    continue
                match = pattern.match(line)
                if match:
                    packages = match.group(1).strip()
                    for pkg in packages.split():
                        pkg = pkg.strip().strip('"').strip("'")
                        if pkg and not pkg.startswith("-"):
                            analysis.dependencies.append(
                                Dependency(
                                    name=pkg,
                                    source_file=analysis.path,
                                    line_number=line_num,
                                    dependency_type="package",
                                )
                            )

            # Extract plugin manager commands
            match = SHELL_PATTERNS["plugin_manager"].search(line)
            if match:
                plugin = match.group(1)
                analysis.dependencies.append(
                    Dependency(
                        name=plugin,
                        source_file=analysis.path,
                        line_number=line_num,
                        dependency_type="plugin",
                    )
                )

    def _parse_gitconfig(self, content: str, analysis: DotfileAnalysis) -> None:
        """Parse gitconfig files."""
        # Extract includes
        include_pattern = re.compile(r"^\s*(?:path|include)\s*=\s*(.+)$", re.MULTILINE)
        for match in include_pattern.finditer(content):
            path = match.group(1).strip()
            analysis.dependencies.append(
                Dependency(
                    name=path,
                    source_file=analysis.path,
                    dependency_type="include",
                )
            )

        # Extract core editor
        editor_pattern = re.compile(r"^\s*editor\s*=\s*(.+)$", re.MULTILINE)
        for match in editor_pattern.finditer(content):
            editor = match.group(1).strip()
            analysis.dependencies.append(
                Dependency(
                    name=editor,
                    source_file=analysis.path,
                    dependency_type="command",
                )
            )

        # Extract merge/diff tools
        tool_pattern = re.compile(r"^\s*(?:tool|cmd)\s*=\s*(.+)$", re.MULTILINE)
        for match in tool_pattern.finditer(content):
            tool = match.group(1).strip()
            analysis.dependencies.append(
                Dependency(
                    name=tool,
                    source_file=analysis.path,
                    dependency_type="command",
                )
            )

    def _parse_toml(self, content: str, analysis: DotfileAnalysis) -> None:
        """Parse TOML configuration files."""
        try:
            import tomllib
        except ImportError:
            # Python < 3.11 fallback
            try:
                import tomli as tomllib
            except ImportError:
                tomllib = None  # type: ignore

        if tomllib:
            try:
                data = tomllib.loads(content)
                self._extract_toml_dependencies(data, analysis)
            except Exception as e:
                analysis.parse_errors.append(f"TOML parse error: {e}")

    def _extract_toml_dependencies(self, data: dict[str, Any], analysis: DotfileAnalysis, prefix: str = "") -> None:
        """Recursively extract dependencies from TOML data."""
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                self._extract_toml_dependencies(value, analysis, full_key)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        # Check if it looks like a command or package
                        if any(c in item for c in ["/", ".", "-"]):
                            analysis.dependencies.append(
                                Dependency(
                                    name=item,
                                    source_file=analysis.path,
                                    dependency_type="config_value",
                                )
                            )
            elif isinstance(value, str):
                # Check for command references
                if any(cmd in value for cmd in ["vim", "nvim", "code", "bat", "fd", "rg"]):
                    analysis.dependencies.append(
                        Dependency(
                            name=value.split()[0],
                            source_file=analysis.path,
                            dependency_type="command",
                        )
                    )

    def _parse_json(self, content: str, analysis: DotfileAnalysis) -> None:
        """Parse JSON configuration files."""
        try:
            data = json.loads(content)
            self._extract_json_dependencies(data, analysis)
        except json.JSONDecodeError as e:
            analysis.parse_errors.append(f"JSON parse error: {e}")

    def _extract_json_dependencies(self, data: Any, analysis: DotfileAnalysis, prefix: str = "") -> None:
        """Recursively extract dependencies from JSON data."""
        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                if key in ("terminal.external.osxExec", "terminal.integrated.shell.*"):
                    analysis.dependencies.append(
                        Dependency(
                            name=str(value),
                            source_file=analysis.path,
                            dependency_type="command",
                        )
                    )
                elif isinstance(value, (dict, list)):
                    self._extract_json_dependencies(value, analysis, full_key)
                elif isinstance(value, str) and any(
                    cmd in value for cmd in ["vim", "nvim", "code", "bash", "zsh"]
                ):
                    analysis.dependencies.append(
                        Dependency(
                            name=value.split()[0],
                            source_file=analysis.path,
                            dependency_type="command",
                        )
                    )
        elif isinstance(data, list):
            for item in data:
                self._extract_json_dependencies(item, analysis)

    def _parse_yaml_file(self, content: str, analysis: DotfileAnalysis) -> None:
        """Parse YAML configuration files."""
        if yaml is None:
            # Fallback: look for patterns
            pattern = re.compile(r"^\s*(\w+):\s*(.+)$", re.MULTILINE)
            for match in pattern.finditer(content):
                key, value = match.group(1), match.group(2).strip()
                if any(cmd in value for cmd in ["vim", "nvim", "bash", "zsh"]):
                    analysis.dependencies.append(
                        Dependency(
                            name=value.split()[0],
                            source_file=analysis.path,
                            dependency_type="command",
                        )
                    )
            return

        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                self._extract_yaml_dependencies(data, analysis)
        except yaml.YAMLError as e:
            analysis.parse_errors.append(f"YAML parse error: {e}")

    def _extract_yaml_dependencies(self, data: dict[str, Any], analysis: DotfileAnalysis, prefix: str = "") -> None:
        """Recursively extract dependencies from YAML data."""
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                self._extract_yaml_dependencies(value, analysis, full_key)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        analysis.dependencies.append(
                            Dependency(
                                name=item,
                                source_file=analysis.path,
                                dependency_type="config_value",
                            )
                        )
            elif isinstance(value, str):
                if any(cmd in value for cmd in ["vim", "nvim", "bash", "zsh"]):
                    analysis.dependencies.append(
                        Dependency(
                            name=value.split()[0],
                            source_file=analysis.path,
                            dependency_type="command",
                        )
                    )

    def _parse_vimrc(self, content: str, analysis: DotfileAnalysis) -> None:
        """Parse Vim/Neovim configuration files."""
        # Extract plugin managers and plugins
        plugin_patterns = [
            re.compile(r"Plug\s+['\"]([^'\"]+)['\"]"),
            re.compile(r"Plugin\s+['\"]([^'\"]+)['\"]"),
            re.compile(r"Bundle\s+['\"]([^'\"]+)['\"]"),
            re.compile(r"use\s*\(\s*\{\s*['\"]([^'\"]+)['\"]"),  # packer.nvim
        ]

        for pattern in plugin_patterns:
            for match in pattern.finditer(content):
                plugin = match.group(1)
                analysis.dependencies.append(
                    Dependency(
                        name=plugin,
                        source_file=analysis.path,
                        dependency_type="plugin",
                    )
                )

        # Extract external commands
        cmd_pattern = re.compile(r"!(\w+)")
        for match in cmd_pattern.finditer(content):
            cmd = match.group(1)
            if cmd not in ("echo", "cd", "ls", "rm", "mkdir"):
                analysis.dependencies.append(
                    Dependency(
                        name=cmd,
                        source_file=analysis.path,
                        dependency_type="command",
                    )
                )

    def _parse_tmux_conf(self, content: str, analysis: DotfileAnalysis) -> None:
        """Parse tmux configuration files."""
        # Extract source commands
        source_pattern = re.compile(r"^\s*source-file\s+(.+)$", re.MULTILINE)
        for match in source_pattern.finditer(content):
            path = match.group(1).strip()
            analysis.dependencies.append(
                Dependency(
                    name=path,
                    source_file=analysis.path,
                    dependency_type="source",
                )
            )

        # Extract run-shell commands
        run_pattern = re.compile(r"^\s*run-shell\s+(.+)$", re.MULTILINE)
        for match in run_pattern.finditer(content):
            cmd = match.group(1).strip()
            analysis.dependencies.append(
                Dependency(
                    name=cmd.split()[0] if cmd else cmd,
                    source_file=analysis.path,
                    dependency_type="command",
                )
            )

        # Extract plugins (tpm)
        plugin_pattern = re.compile(r"set\s+-g\s+@plugin\s+['\"]?([^'\"]+)['\"]?")
        for match in plugin_pattern.finditer(content):
            plugin = match.group(1).strip()
            analysis.dependencies.append(
                Dependency(
                    name=plugin,
                    source_file=analysis.path,
                    dependency_type="plugin",
                )
            )
