"""Import dotfiles from other managers (chezmoi, stow, dotbot)."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from dotsync.analyzer import DotfileAnalyzer
from dotsync.models import DotfileAnalysis


class DotfileImporter:
    """Imports dotfiles from other managers."""

    def __init__(self, source_path: str | Path, target_path: str | Path):
        self.source_path = Path(source_path)
        self.target_path = Path(target_path)

    def import_from_chezmoi(self) -> list[str]:
        """Import from chezmoi source state."""
        if not self.source_path.exists():
            raise FileNotFoundError(f"Source path not found: {self.source_path}")

        imported = []
        chezmoi_dir = self.source_path

        # chezmoi stores files in the source state directory
        # with the target path encoded in the filename
        for file_path in chezmoi_dir.rglob("*"):
            if file_path.is_file():
                # chezmoi uses prefixes like dot_ for .file, run_ for scripts, etc.
                target_name = self._chezmoi_to_target(file_path.name)
                if target_name:
                    target_file = self.target_path / target_name
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, target_file)
                    imported.append(str(target_file))

        return imported

    def _chezmoi_to_target(self, filename: str) -> str | None:
        """Convert chezmoi filename to target filename."""
        # dot_file -> .file
        if filename.startswith("dot_"):
            return "." + filename[4:]

        # exact_file -> exact_file
        if filename.startswith("exact_"):
            return filename[6:]

        # symlink_file -> symlink (handled separately)
        if filename.startswith("symlink_"):
            return None  # Skip symlinks for now

        # run_ scripts are not dotfiles
        if filename.startswith("run_"):
            return None

        return filename

    def import_from_stow(self) -> list[str]:
        """Import from GNU Stow directory structure."""
        if not self.source_path.exists():
            raise FileNotFoundError(f"Source path not found: {self.source_path}")

        imported = []

        # Stow uses a directory per package, with the dotfile structure inside
        for package_dir in self.source_path.iterdir():
            if package_dir.is_dir():
                for file_path in package_dir.rglob("*"):
                    if file_path.is_file():
                        # Stow mirrors the home directory structure
                        relative = file_path.relative_to(package_dir)
                        target_file = self.target_path / relative
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file_path, target_file)
                        imported.append(str(target_file))

        return imported

    def import_from_dotbot(self) -> list[str]:
        """Import from dotbot configuration."""
        if not self.source_path.exists():
            raise FileNotFoundError(f"Source path not found: {self.source_path}")

        imported = []

        # Dotbot uses a YAML config file (usually install.conf.yaml)
        config_files = list(self.source_path.glob("*.conf.yaml")) + list(
            self.source_path.glob("*.conf.yml")
        )

        for config_file in config_files:
            try:
                import yaml

                with open(config_file) as f:
                    config = yaml.safe_load(f)

                if isinstance(config, list):
                    for section in config:
                        if isinstance(section, dict):
                            # Handle 'link' section
                            if "link" in section:
                                for target, source in section["link"].items():
                                    target_path = Path(target).expanduser()
                                    source_path = self.source_path / source
                                    if source_path.exists():
                                        target_path.parent.mkdir(
                                            parents=True, exist_ok=True
                                        )
                                        shutil.copy2(source_path, target_path)
                                        imported.append(str(target_path))

                            # Handle 'create' section
                            if "create" in section:
                                for path in section["create"]:
                                    create_path = self.target_path / path
                                    create_path.parent.mkdir(parents=True, exist_ok=True)
                                    create_path.mkdir(exist_ok=True)
                                    imported.append(str(create_path))

            except ImportError:
                pass

        return imported

    def import_from_any(self, manager_type: str | None = None) -> list[str]:
        """Auto-detect and import from any supported manager."""
        if manager_type:
            importers = {
                "chezmoi": self.import_from_chezmoi,
                "stow": self.import_from_stow,
                "dotbot": self.import_from_dotbot,
            }
            if manager_type in importers:
                return importers[manager_type]()
            raise ValueError(f"Unknown manager type: {manager_type}")

        # Auto-detect
        if (self.source_path / ".chezmoiroot").exists() or any(
            f.name.startswith("dot_") for f in self.source_path.iterdir()
        ):
            return self.import_from_chezmoi()
        elif any(
            d.is_dir()
            and any(f.is_file() for f in d.rglob("*"))
            for d in self.source_path.iterdir()
        ):
            return self.import_from_stow()
        elif any(self.source_path.glob("*.conf.yaml")) or any(
            self.source_path.glob("*.conf.yml")
        ):
            return self.import_from_dotbot()

        raise ValueError("Could not auto-detect dotfile manager")
