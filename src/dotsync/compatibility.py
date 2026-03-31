"""Cross-platform compatibility checks for dotfiles."""

from __future__ import annotations

import json
import platform
from pathlib import Path
from typing import Any

from dotsync.models import (
    CompatibilityIssue,
    Dependency,
    DotfileAnalysis,
    PlatformDefinition,
    Severity,
)


# Default platform definitions
DEFAULT_PLATFORMS: dict[str, dict[str, Any]] = {
    "macos": {
        "name": "macos",
        "package_manager": "brew",
        "shell_default": "/bin/zsh",
        "config_paths": {
            "zshrc": "~/.zshrc",
            "bashrc": "~/.bashrc",
            "gitconfig": "~/.gitconfig",
            "tmux": "~/.tmux.conf",
            "vimrc": "~/.vimrc",
        },
        "package_map": {
            "starship": "starship",
            "fzf": "fzf",
            "ripgrep": "ripgrep",
            "fd": "fd",
            "bat": "bat",
            "eza": "eza",
            "zoxide": "zoxide",
            "tmux": "tmux",
            "neovim": "neovim",
            "git": "git",
            "zsh": "zsh",
            "bash": "bash",
        },
        "incompatible_tools": ["apt", "apt-get", "pacman", "dnf", "yum", "systemctl"],
        "supported_shells": ["bash", "zsh", "fish"],
        "os_family": "darwin",
        "arch_support": ["x86_64", "arm64"],
    },
    "linux-ubuntu": {
        "name": "linux-ubuntu",
        "package_manager": "apt",
        "shell_default": "/bin/bash",
        "config_paths": {
            "zshrc": "~/.zshrc",
            "bashrc": "~/.bashrc",
            "gitconfig": "~/.gitconfig",
            "tmux": "~/.tmux.conf",
            "vimrc": "~/.vimrc",
        },
        "package_map": {
            "starship": "starship",
            "fzf": "fzf",
            "ripgrep": "ripgrep",
            "fd": "fd-find",
            "bat": "bat",
            "eza": "eza",
            "zoxide": "zoxide",
            "tmux": "tmux",
            "neovim": "neovim",
            "git": "git",
            "zsh": "zsh",
            "bash": "bash",
        },
        "incompatible_tools": ["brew", "mas", "pacman", "dnf", "yum", "systemctl"],
        "supported_shells": ["bash", "zsh", "fish"],
        "os_family": "linux",
        "arch_support": ["x86_64", "arm64"],
    },
    "linux-arch": {
        "name": "linux-arch",
        "package_manager": "pacman",
        "shell_default": "/bin/bash",
        "config_paths": {
            "zshrc": "~/.zshrc",
            "bashrc": "~/.bashrc",
            "gitconfig": "~/.gitconfig",
            "tmux": "~/.tmux.conf",
            "vimrc": "~/.vimrc",
        },
        "package_map": {
            "starship": "starship",
            "fzf": "fzf",
            "ripgrep": "ripgrep",
            "fd": "fd",
            "bat": "bat",
            "eza": "eza",
            "zoxide": "zoxide",
            "tmux": "tmux",
            "neovim": "neovim",
            "git": "git",
            "zsh": "zsh",
            "bash": "bash",
        },
        "incompatible_tools": ["brew", "mas", "apt", "apt-get", "dnf", "yum"],
        "supported_shells": ["bash", "zsh", "fish"],
        "os_family": "linux",
        "arch_support": ["x86_64"],
    },
    "linux-fedora": {
        "name": "linux-fedora",
        "package_manager": "dnf",
        "shell_default": "/bin/bash",
        "config_paths": {
            "zshrc": "~/.zshrc",
            "bashrc": "~/.bashrc",
            "gitconfig": "~/.gitconfig",
            "tmux": "~/.tmux.conf",
            "vimrc": "~/.vimrc",
        },
        "package_map": {
            "starship": "starship",
            "fzf": "fzf",
            "ripgrep": "ripgrep",
            "fd": "fd-find",
            "bat": "bat",
            "eza": "eza",
            "zoxide": "zoxide",
            "tmux": "tmux",
            "neovim": "neovim",
            "git": "git",
            "zsh": "zsh",
            "bash": "bash",
        },
        "incompatible_tools": ["brew", "mas", "apt", "apt-get", "pacman", "yum"],
        "supported_shells": ["bash", "zsh", "fish"],
        "os_family": "linux",
        "arch_support": ["x86_64", "arm64"],
    },
}


class CompatibilityChecker:
    """Checks dotfile compatibility across different platforms."""

    def __init__(self, platforms_dir: str | Path | None = None):
        self.platforms_dir = Path(platforms_dir) if platforms_dir else None
        self.platforms: dict[str, PlatformDefinition] = {}
        self._load_platforms()

    def _load_platforms(self) -> None:
        """Load platform definitions from defaults and custom files."""
        # Load default platforms
        for name, data in DEFAULT_PLATFORMS.items():
            self.platforms[name] = PlatformDefinition(**data)

        # Load custom platforms from directory
        if self.platforms_dir and self.platforms_dir.exists():
            for file_path in self.platforms_dir.glob("*.json"):
                try:
                    data = json.loads(file_path.read_text())
                    name = data.get("name", file_path.stem)
                    self.platforms[name] = PlatformDefinition(**data)
                except (json.JSONDecodeError, Exception) as e:
                    print(f"Warning: Failed to load platform {file_path}: {e}")

    def check_compatibility(
        self,
        analyses: list[DotfileAnalysis],
        target_platform: str,
        source_platform: str | None = None,
    ) -> list[CompatibilityIssue]:
        """Check compatibility of analyzed dotfiles with a target platform."""
        if target_platform not in self.platforms:
            raise ValueError(f"Unknown platform: {target_platform}")

        target = self.platforms[target_platform]
        source = self.platforms.get(source_platform) if source_platform else None

        issues: list[CompatibilityIssue] = []

        for analysis in analyses:
            # Check for incompatible tools
            issues.extend(self._check_incompatible_tools(analysis, target))

            # Check for missing dependencies
            issues.extend(self._check_missing_dependencies(analysis, target))

            # Check shell compatibility
            issues.extend(self._check_shell_compatibility(analysis, target))

            # Check path differences
            issues.extend(self._check_path_differences(analysis, target, source))

            # Check OS-specific configurations
            issues.extend(self._check_os_specific_configs(analysis, target, source))

        return issues

    def _check_incompatible_tools(
        self,
        analysis: DotfileAnalysis,
        target: PlatformDefinition,
    ) -> list[CompatibilityIssue]:
        """Check for tools that are incompatible with the target platform."""
        issues = []

        for dep in analysis.dependencies:
            if dep.name in target.incompatible_tools:
                issues.append(
                    CompatibilityIssue(
                        severity=Severity.ERROR,
                        message=f"Tool '{dep.name}' is not compatible with {target.name}",
                        source=dep.source_file,
                        target=target.name,
                        suggestion=f"Replace '{dep.name}' with an alternative for {target.name}",
                        affected_files=[analysis.path],
                    )
                )

        # Check environment variables for incompatible tools
        for var_name, var_value in analysis.environment_variables.items():
            for tool in target.incompatible_tools:
                if tool in var_value:
                    issues.append(
                        CompatibilityIssue(
                            severity=Severity.WARNING,
                            message=f"Environment variable '{var_name}' references incompatible tool '{tool}'",
                            source=analysis.path,
                            target=target.name,
                            suggestion=f"Update '{var_name}' to use a compatible alternative",
                            affected_files=[analysis.path],
                        )
                    )

        return issues

    def _check_missing_dependencies(
        self,
        analysis: DotfileAnalysis,
        target: PlatformDefinition,
    ) -> list[CompatibilityIssue]:
        """Check for dependencies that may not be available on target platform."""
        issues = []

        for dep in analysis.dependencies:
            if dep.dependency_type == "package" and dep.name not in target.package_map:
                # Check if it's a known package that might need manual installation
                issues.append(
                    CompatibilityIssue(
                        severity=Severity.WARNING,
                        message=f"Package '{dep.name}' not found in {target.name} package map",
                        source=analysis.path,
                        target=target.name,
                        suggestion=f"Verify '{dep.name}' can be installed via {target.package_manager}",
                        affected_files=[analysis.path],
                    )
                )

        return issues

    def _check_shell_compatibility(
        self,
        analysis: DotfileAnalysis,
        target: PlatformDefinition,
    ) -> list[CompatibilityIssue]:
        """Check for shell-specific features that may not work on target."""
        issues = []

        # Check for bash-specific syntax in zsh files and vice versa
        if analysis.file_type == "bash" and "zsh" not in target.supported_shells:
            issues.append(
                CompatibilityIssue(
                    severity=Severity.INFO,
                    message=f"Bash-specific configurations may need adaptation for {target.name}",
                    source=analysis.path,
                    target=target.name,
                    suggestion="Review shell-specific features for compatibility",
                    affected_files=[analysis.path],
                )
            )

        # Check for zsh-specific features
        if analysis.file_type == "zsh":
            zsh_specific = ["autoload", "zstyle", "zle", "compinit", "precmd", "chpwd"]
            for func in analysis.functions:
                if any(z in func for z in zsh_specific):
                    if "zsh" not in target.supported_shells:
                        issues.append(
                            CompatibilityIssue(
                                severity=Severity.WARNING,
                                message=f"Zsh-specific function '{func}' may not work on {target.name}",
                                source=analysis.path,
                                target=target.name,
                                suggestion="Consider using shell-agnostic alternatives",
                                affected_files=[analysis.path],
                            )
                        )

        return issues

    def _check_path_differences(
        self,
        analysis: DotfileAnalysis,
        target: PlatformDefinition,
        source: PlatformDefinition | None = None,
    ) -> list[CompatibilityIssue]:
        """Check for path differences between platforms."""
        issues = []

        # Check if config paths differ
        if source:
            for config_name, source_path in source.config_paths.items():
                if config_name in target.config_paths:
                    target_path = target.config_paths[config_name]
                    if source_path != target_path:
                        # Check if this file is in our analysis
                        if any(config_name in a.path for a in [analysis]):
                            issues.append(
                                CompatibilityIssue(
                                    severity=Severity.INFO,
                                    message=f"Config path for '{config_name}' differs: {source_path} -> {target_path}",
                                    source=source.name,
                                    target=target.name,
                                    suggestion=f"Update path references from '{source_path}' to '{target_path}'",
                                    affected_files=[analysis.path],
                                )
                            )

        return issues

    def _check_os_specific_configs(
        self,
        analysis: DotfileAnalysis,
        target: PlatformDefinition,
        source: PlatformDefinition | None = None,
    ) -> list[CompatibilityIssue]:
        """Check for OS-specific configuration issues."""
        issues = []

        # Check for macOS-specific tools
        macos_tools = ["mas", "osascript", "defaults", "pbcopy", "pbpaste", "open"]
        if target.os_family != "darwin":
            for dep in analysis.dependencies:
                if dep.name in macos_tools:
                    issues.append(
                        CompatibilityIssue(
                            severity=Severity.ERROR,
                            message=f"macOS-specific tool '{dep.name}' not available on {target.name}",
                            source=analysis.path,
                            target=target.name,
                            suggestion=f"Find an alternative to '{dep.name}' for {target.name}",
                            affected_files=[analysis.path],
                        )
                    )

        # Check for Linux-specific tools
        linux_tools = ["systemctl", "xclip", "xsel", "xdg-open", "notify-send"]
        if target.os_family == "darwin":
            for dep in analysis.dependencies:
                if dep.name in linux_tools:
                    issues.append(
                        CompatibilityIssue(
                            severity=Severity.WARNING,
                            message=f"Linux-specific tool '{dep.name}' may not be available on {target.name}",
                            source=analysis.path,
                            target=target.name,
                            suggestion=f"Find a macOS alternative to '{dep.name}'",
                            affected_files=[analysis.path],
                        )
                    )

        return issues

    def get_package_mapping(self, package: str, target_platform: str) -> str | None:
        """Get the target platform package name for a given package."""
        if target_platform not in self.platforms:
            return None

        target = self.platforms[target_platform]
        return target.package_map.get(package)

    def get_install_command(self, package: str, target_platform: str) -> str:
        """Get the installation command for a package on a target platform."""
        if target_platform not in self.platforms:
            return f"# Unknown platform: {target_platform}"

        target = self.platforms[target_platform]
        pkg = target.package_map.get(package, package)

        commands = {
            "brew": f"brew install {pkg}",
            "apt": f"sudo apt install -y {pkg}",
            "pacman": f"sudo pacman -S --noconfirm {pkg}",
            "dnf": f"sudo dnf install -y {pkg}",
        }

        return commands.get(target.package_manager, f"# Install {pkg}")

    def detect_current_platform(self) -> str:
        """Detect the current platform."""
        system = platform.system().lower()
        if system == "darwin":
            return "macos"

        # Try to detect Linux distribution
        try:
            import distro

            distro_id = distro.id()
            if "ubuntu" in distro_id:
                return "linux-ubuntu"
            elif "arch" in distro_id:
                return "linux-arch"
            elif "fedora" in distro_id:
                return "linux-fedora"
        except ImportError:
            pass

        # Fallback to generic linux
        if system == "linux":
            return "linux-ubuntu"  # Default to Ubuntu

        return "unknown"
