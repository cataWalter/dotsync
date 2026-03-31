"""Interactive migration wizard for DotSync."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm, Prompt

from dotsync.analyzer import DotfileAnalyzer
from dotsync.compatibility import CompatibilityChecker
from dotsync.conflict_detector import ConflictDetector
from dotsync.generator import MigrationGenerator

console = Console()


class MigrationWizard:
    """Interactive wizard for dotfile migration."""

    def __init__(self):
        self.checker = CompatibilityChecker()

    def run(self) -> None:
        """Run the interactive migration wizard."""
        console.print("\n[bold blue]DotSync Migration Wizard[/bold blue]\n")

        # Step 1: Get source path
        source_path = Prompt.ask(
            "Path to your dotfiles directory",
            default="~/.dotfiles",
        )
        source_path = Path(source_path).expanduser()

        if not source_path.exists():
            console.print(f"[red]Error:[/red] Path not found: {source_path}")
            return

        # Step 2: Detect source platform
        detected_platform = self.checker.detect_current_platform()
        source_platform = Prompt.ask(
            "Source platform",
            default=detected_platform,
            choices=list(self.checker.platforms.keys()),
        )

        # Step 3: Get target platform
        console.print("\n[bold]Available target platforms:[/bold]")
        for platform in self.checker.platforms:
            p = self.checker.platforms[platform]
            console.print(f"  - {platform} ({p.package_manager}, {p.os_family})")

        target_platform = Prompt.ask(
            "\nTarget platform",
            default="linux-ubuntu" if source_platform == "macos" else "macos",
            choices=list(self.checker.platforms.keys()),
        )

        # Step 4: Analyze
        console.print(f"\n[dim]Analyzing {source_path}...[/dim]")
        analyzer = DotfileAnalyzer(source_path)
        analyses = analyzer.analyze_all()

        total_deps = sum(len(a.dependencies) for a in analyses)
        console.print(f"[green]Found {len(analyses)} files with {total_deps} dependencies[/green]")

        # Step 5: Check compatibility
        console.print(f"\n[dim]Checking compatibility with {target_platform}...[/dim]")
        issues = self.checker.check_compatibility(analyses, target_platform, source_platform)

        if issues:
            console.print(f"\n[yellow]Found {len(issues)} compatibility issue(s):[/yellow]")
            for issue in issues[:5]:
                console.print(f"  - [{issue.severity.value}] {issue.message}")
            if len(issues) > 5:
                console.print(f"  ... and {len(issues) - 5} more")

            if not Confirm.ask("\nContinue with migration despite issues?", default=True):
                console.print("[yellow]Migration cancelled.[/yellow]")
                return

        # Step 6: Check conflicts
        conflict_detector = ConflictDetector()
        conflicts = conflict_detector.detect_conflicts(analyses)

        if conflicts:
            console.print(f"\n[yellow]Found {len(conflicts)} conflict(s):[/yellow]")
            for conflict in conflicts[:3]:
                console.print(f"  - [{conflict.severity.value}] {conflict.description}")
            if len(conflicts) > 3:
                console.print(f"  ... and {len(conflicts) - 3} more")

            if not Confirm.ask("\nContinue with migration despite conflicts?", default=True):
                console.print("[yellow]Migration cancelled.[/yellow]")
                return

        # Step 7: Generate migration plan
        console.print("\n[dim]Generating migration plan...[/dim]")
        generator = MigrationGenerator()
        plan = generator.generate_migration_script(
            analyses=analyses,
            target_platform=target_platform,
            source_platform=source_platform,
            compatibility_checker=self.checker,
            conflict_detector=conflict_detector,
        )

        # Step 8: Summary
        console.print("\n[bold green]Migration Plan Summary[/bold green]")
        console.print(f"  Source: {source_platform}")
        console.print(f"  Target: {target_platform}")
        console.print(f"  Steps: {len(plan.steps)}")
        console.print(f"  Estimated time: {plan.estimated_time}")

        # Step 9: Show steps
        if Confirm.ask("\nShow migration steps?", default=False):
            console.print("\n[bold]Steps:[/bold]")
            for step in plan.steps:
                console.print(f"  {step.order}. [{step.action}] {step.description}")
                console.print(f"     Command: {step.command}")

        # Step 10: Output
        output_path = Prompt.ask(
            "\nOutput file for migration script",
            default="migration.sh",
        )

        script = generator.render_install_script(plan)
        output = Path(output_path)
        generator.save_script(script, output)

        console.print(f"\n[bold green]Migration script saved to: {output}[/bold green]")
        console.print("\n[dim]Run with DRY_RUN=true to preview changes before applying.[/dim]")
