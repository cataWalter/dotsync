"""Migration script generator using Jinja2 templates."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from dotsync.compatibility import CompatibilityChecker
from dotsync.conflict_detector import ConflictDetector
from dotsync.models import (
    AnalysisReport,
    DotfileAnalysis,
    MigrationPlan,
    MigrationStep,
    PlatformDefinition,
)

# Default templates as fallback strings
INSTALL_SCRIPT_TEMPLATE = """#!/usr/bin/env bash
# DotSync Migration Script
# Generated: {{ generated_at }}
# Source: {{ source_platform }}
# Target: {{ target_platform }}
#
# WARNING: Review this script before running!
# Run with --dry-run first to see what will happen.

set -euo pipefail

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running in dry-run mode
DRY_RUN={{ dry_run | lower }}
run_cmd() {
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] Would execute: $*"
    else
        log_info "Executing: $*"
        eval "$@"
    fi
}

# Backup existing configurations
backup_configs() {
    local backup_dir="$HOME/.dotsync_backup_{{ timestamp }}"
    log_info "Creating backup in $backup_dir"
    mkdir -p "$backup_dir"

{% for file in backup_files %}
    if [ -f "{{ file }}" ]; then
        cp -r "{{ file }}" "$backup_dir/"
        log_info "Backed up {{ file }}"
    fi
{% endfor %}

    log_info "Backup complete"
}

# Install dependencies
install_dependencies() {
    log_info "Installing dependencies for {{ target_platform }}"

{% for step in steps %}
{% if step.action == "install" %}
    # {{ step.description }}
{% if step.condition %}
    if {{ step.condition }}; then
        run_cmd "{{ step.command }}"
    else
        log_info "Skipping: {{ step.description }} (condition not met)"
    fi
{% else %}
    run_cmd "{{ step.command }}"
{% endif %}

{% endif %}
{% endfor %}
}

# Configure dotfiles
configure_dotfiles() {
    log_info "Configuring dotfiles"

{% for step in steps %}
{% if step.action in ["copy", "modify", "create"] %}
    # {{ step.description }}
{% if step.condition %}
    if {{ step.condition }}; then
        run_cmd "{{ step.command }}"
    fi
{% else %}
    run_cmd "{{ step.command }}"
{% endif %}

{% endif %}
{% endfor %}
}

# Post-installation checks
post_install() {
    log_info "Running post-installation checks"

{% for step in steps %}
{% if step.action == "verify" %}
    # {{ step.description }}
    run_cmd "{{ step.command }}" || log_warn "{{ step.description }} failed"

{% endif %}
{% endfor %}
}

# Main execution
main() {
    log_info "Starting DotSync migration: {{ source_platform }} -> {{ target_platform }}"

    # Create backup
    backup_configs

    # Install dependencies
    install_dependencies

    # Configure dotfiles
    configure_dotfiles

    # Post-installation
    post_install

    log_info "Migration complete!"
{% if issues %}
    log_warn "There were {{ issues | length }} compatibility issue(s). Review the report for details."
{% endif %}
}

# Run main function
main "$@"
"""

ROLLBACK_SCRIPT_TEMPLATE = """#!/usr/bin/env bash
# DotSync Rollback Script
# Generated: {{ generated_at }}
# Reverts migration from {{ source_platform }} to {{ target_platform }}

set -euo pipefail

RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Restore from backup
restore_backup() {
    local backup_dir="$HOME/.dotsync_backup_{{ timestamp }}"

    if [ ! -d "$backup_dir" ]; then
        echo -e "${RED}[ERROR]${NC} Backup directory not found: $backup_dir"
        exit 1
    fi

    log_info "Restoring from backup: $backup_dir"

{% for file in backup_files %}
    if [ -f "$backup_dir/{{ file | basename }}" ]; then
        cp -r "$backup_dir/{{ file | basename }}" "{{ file }}"
        log_info "Restored {{ file }}"
    fi
{% endfor %}

    log_info "Rollback complete"
}

main() {
    log_info "Starting rollback..."
    restore_backup
}

main "$@"
"""

REPORT_TEMPLATE = """# DotSync Compatibility Report

Generated: {{ generated_at }}

## Summary

- **Source Platform**: {{ source_platform }}
- **Target Platform**: {{ target_platform }}
- **Files Analyzed**: {{ files_analyzed }}
- **Total Dependencies**: {{ total_dependencies }}
- **Compatibility Issues**: {{ total_issues }}
- **Conflicts Detected**: {{ conflicts | length }}

## Analyzed Files

{% for file in analyzed_files %}
### {{ file.path }}

- **Type**: {{ file.file_type }}
- **Dependencies**: {{ file.dependencies | length }}
- **Environment Variables**: {{ file.environment_variables | length }}
- **Aliases**: {{ file.aliases | length }}
- **Functions**: {{ file.functions | length }}
{% if file.parse_errors %}
- **Parse Errors**: {{ file.parse_errors | join(", ") }}
{% endif %}
{% endfor %}

## Compatibility Issues

{% for platform, issues in platform_compatibility.items() %}
### {{ platform }}

{% for issue in issues %}
- **{{ issue.severity.value.upper() }}**: {{ issue.message }}
  - Suggestion: {{ issue.suggestion }}
{% endfor %}
{% endfor %}

## Conflicts

{% for conflict in conflicts %}
### {{ conflict.description }}

- **Severity**: {{ conflict.severity.value.upper() }}
- **Affected**: {{ conflict.affected_variable }}
- **Resolution**: {{ conflict.resolution }}
{% endfor %}

## Dependency Graph

```mermaid
{{ dependency_graph }}
```
"""


class MigrationGenerator:
    """Generates migration scripts and reports using Jinja2 templates."""

    def __init__(self, templates_dir: str | Path | None = None):
        self.templates_dir = Path(templates_dir) if templates_dir else None
        self.env = self._create_jinja_env()

    def _create_jinja_env(self) -> Environment:
        """Create Jinja2 environment with appropriate loaders."""
        if self.templates_dir and self.templates_dir.exists():
            env = Environment(
                loader=FileSystemLoader(str(self.templates_dir)),
                autoescape=select_autoescape(),
                trim_blocks=True,
                lstrip_blocks=True,
            )
        else:
            # Use string templates as fallback
            env = Environment(
                autoescape=select_autoescape(),
                trim_blocks=True,
                lstrip_blocks=True,
            )

        # Add custom filters
        import os

        def basename_filter(path: str) -> str:
            """Get the basename of a path."""
            return os.path.basename(path)

        env.filters["basename"] = basename_filter

        # Validate templates
        env.from_string(INSTALL_SCRIPT_TEMPLATE)
        env.from_string(ROLLBACK_SCRIPT_TEMPLATE)
        env.from_string(REPORT_TEMPLATE)
        return env

    def generate_migration_script(
        self,
        analyses: list[DotfileAnalysis],
        target_platform: str,
        source_platform: str | None = None,
        compatibility_checker: CompatibilityChecker | None = None,
        conflict_detector: ConflictDetector | None = None,
    ) -> MigrationPlan:
        """Generate a complete migration plan."""
        checker = compatibility_checker or CompatibilityChecker()
        detector = conflict_detector or ConflictDetector()

        # Get platform info
        if target_platform not in checker.platforms:
            raise ValueError(f"Unknown target platform: {target_platform}")

        target = checker.platforms[target_platform]
        checker.platforms.get(source_platform) if source_platform else None

        # Detect conflicts
        conflicts = detector.detect_conflicts(analyses)

        # Check compatibility
        issues = checker.check_compatibility(analyses, target_platform, source_platform)

        # Generate migration steps
        steps = self._generate_steps(analyses, target, checker)

        # Estimate time
        estimated_time = self._estimate_time(steps)

        return MigrationPlan(
            source_platform=source_platform or "unknown",
            target_platform=target_platform,
            steps=steps,
            issues=issues,
            conflicts=conflicts,
            estimated_time=estimated_time,
            backup_required=True,
        )

    def _generate_steps(
        self,
        analyses: list[DotfileAnalysis],
        target: PlatformDefinition,
        checker: CompatibilityChecker,
    ) -> list[MigrationStep]:
        """Generate individual migration steps."""
        steps: list[MigrationStep] = []
        order = 1

        # Step 1: Install package manager if needed
        steps.append(
            MigrationStep(
                order=order,
                action="install",
                description=f"Ensure {target.package_manager} is installed",
                command=self._get_package_manager_install(target),
                condition=f"! command -v {target.package_manager}",
                rollback_command="",
            )
        )
        order += 1

        # Step 2: Install dependencies
        all_packages = self._collect_packages(analyses)
        for pkg in all_packages:
            mapped_pkg = checker.get_package_mapping(pkg, target.name)
            if mapped_pkg:
                install_cmd = checker.get_install_command(pkg, target.name)
                steps.append(
                    MigrationStep(
                        order=order,
                        action="install",
                        description=f"Install {pkg}",
                        command=install_cmd,
                        condition=f"! command -v {pkg}",
                        rollback_command=f"{target.package_manager} remove {mapped_pkg}",
                    )
                )
                order += 1

        # Step 3: Copy/symlink dotfiles
        for analysis in analyses:
            if analysis.file_type in ("bash", "zsh", "sh", "gitconfig", "vim", "tmux"):
                target_path = self._get_target_path(analysis, target)
                steps.append(
                    MigrationStep(
                        order=order,
                        action="copy",
                        description=f"Copy {analysis.path} to {target_path}",
                        command=f'cp "{analysis.path}" "{target_path}"',
                        rollback_command=f'rm -f "{target_path}"',
                    )
                )
                order += 1

        # Step 4: Shell-specific setup
        if target.shell_default != "/bin/bash":
            steps.append(
                MigrationStep(
                    order=order,
                    action="modify",
                    description=f"Set default shell to {target.shell_default}",
                    command=f'chsh -s {target.shell_default}',
                    condition=f'[ "$SHELL" != "{target.shell_default}" ]',
                )
            )
            order += 1

        # Step 5: Verify installation
        steps.append(
            MigrationStep(
                order=order,
                action="verify",
                description="Verify all tools are installed",
                command=" && ".join(
                    [f"command -v {pkg}" for pkg in list(all_packages)[:5]]
                ) or "true",
            )
        )

        return steps

    def _collect_packages(self, analyses: list[DotfileAnalysis]) -> set[str]:
        """Collect all unique packages from analyses."""
        packages = set()
        for analysis in analyses:
            for dep in analysis.dependencies:
                if dep.dependency_type == "package":
                    packages.add(dep.name)
        return packages

    def _get_target_path(self, analysis: DotfileAnalysis, target: PlatformDefinition) -> str:
        """Get the target path for a dotfile."""
        # Map common files
        file_name = Path(analysis.path).name

        if file_name in target.config_paths:
            return target.config_paths[file_name].replace("~", "$HOME")

        # Default to same relative path
        return f"$HOME/{file_name}"

    def _get_package_manager_install(self, target: PlatformDefinition) -> str:
        """Get command to install the package manager if missing."""
        installs = {
            "brew": '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"',
            "apt": "sudo apt update && sudo apt install -y build-essential",
            "pacman": "sudo pacman -Syu",
            "dnf": "sudo dnf update",
        }
        return installs.get(target.package_manager, f"# Install {target.package_manager}")

    def _estimate_time(self, steps: list[MigrationStep]) -> str:
        """Estimate migration time based on steps."""
        install_steps = sum(1 for s in steps if s.action == "install")
        copy_steps = sum(1 for s in steps if s.action == "copy")

        # Rough estimate: 30s per install, 5s per copy
        total_seconds = install_steps * 30 + copy_steps * 5

        if total_seconds < 60:
            return f"~{total_seconds} seconds"
        elif total_seconds < 3600:
            return f"~{total_seconds // 60} minutes"
        else:
            return f"~{total_seconds // 3600} hours"

    def render_install_script(self, plan: MigrationPlan, dry_run: bool = False) -> str:
        """Render the installation script from a migration plan."""
        template = self.env.from_string(INSTALL_SCRIPT_TEMPLATE)

        backup_files = []
        for step in plan.steps:
            if step.action == "copy":
                # Extract target file from command
                if 'cp "' in step.command:
                    parts = step.command.split('"')
                    if len(parts) >= 4:
                        backup_files.append(parts[3])

        return template.render(
            generated_at=datetime.now().isoformat(),
            source_platform=plan.source_platform,
            target_platform=plan.target_platform,
            dry_run=dry_run,
            timestamp=datetime.now().strftime("%Y%m%d_%H%M%S"),
            backup_files=backup_files,
            steps=plan.steps,
            issues=plan.issues,
        )

    def render_rollback_script(self, plan: MigrationPlan) -> str:
        """Render the rollback script from a migration plan."""
        template = self.env.from_string(ROLLBACK_SCRIPT_TEMPLATE)

        backup_files = []
        for step in plan.steps:
            if step.action == "copy":
                if 'cp "' in step.command:
                    parts = step.command.split('"')
                    if len(parts) >= 4:
                        backup_files.append(parts[3])

        return template.render(
            generated_at=datetime.now().isoformat(),
            source_platform=plan.source_platform,
            target_platform=plan.target_platform,
            timestamp=datetime.now().strftime("%Y%m%d_%H%M%S"),
            backup_files=backup_files,
        )

    def render_report(
        self,
        report: AnalysisReport,
        target_platform: str,
    ) -> str:
        """Render a compatibility report."""
        template = self.env.from_string(REPORT_TEMPLATE)

        return template.render(
            generated_at=datetime.now().isoformat(),
            source_platform=report.source_path,
            target_platform=target_platform,
            files_analyzed=len(report.analyzed_files),
            total_dependencies=report.total_dependencies,
            total_issues=report.total_issues,
            analyzed_files=report.analyzed_files,
            platform_compatibility=report.platform_compatibility,
            conflicts=report.conflicts,
            dependency_graph=report.dependency_graph.to_mermaid(),
        )

    def save_script(self, content: str, output_path: str | Path) -> Path:
        """Save a script to a file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        path.chmod(0o755)
        return path
