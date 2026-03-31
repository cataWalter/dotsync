"""CLI entry point for DotSync using Typer."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from dotsync.analyzer import DotfileAnalyzer
from dotsync.compatibility import CompatibilityChecker
from dotsync.conflict_detector import ConflictDetector
from dotsync.dependency_graph import DependencyGraphBuilder
from dotsync.generator import MigrationGenerator
from dotsync.models import AnalysisReport

app = typer.Typer(
    name="dotsync",
    help="Intelligent Dotfile Migration & Compatibility Analyzer",
    add_completion=False,
    rich_markup_mode="rich",
    invoke_without_command=True,
)

console = Console()


def _get_version() -> str:
    """Get the current version of DotSync."""
    try:
        from dotsync import __version__

        return __version__
    except ImportError:
        return "0.1.0"


@app.callback()
def callback(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit.",
    ),
) -> None:
    """DotSync - Intelligent Dotfile Migration & Compatibility Analyzer"""
    if version:
        console.print(f"DotSync v{_get_version()}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command()
def analyze(
    path: str = typer.Argument(
        "~/.dotfiles", help="Path to the dotfiles directory to analyze."
    ),
    output: str = typer.Option(
        None, "--output", "-o", help="Output file for the analysis report (JSON)."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", help="Show detailed analysis output."
    ),
) -> None:
    """Analyze dotfiles and extract dependencies."""
    path = Path(path).expanduser()

    if not path.exists():
        console.print(f"[red]Error:[/red] Path not found: {path}")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing dotfiles...", total=None)

        analyzer = DotfileAnalyzer(path)
        analyses = analyzer.analyze_all()

        progress.update(task, description="Building dependency graph...")
        graph_builder = DependencyGraphBuilder()
        dep_graph = graph_builder.build(analyses)

        progress.update(task, description="Detecting conflicts...")
        conflict_detector = ConflictDetector()
        conflicts = conflict_detector.detect_conflicts(analyses)

    # Build report
    total_deps = sum(len(a.dependencies) for a in analyses)

    report = AnalysisReport(
        source_path=str(path),
        analyzed_files=analyses,
        dependency_graph=dep_graph,
        total_dependencies=total_deps,
        total_issues=len(conflicts),
        conflicts=conflicts,
    )

    # Output results
    if output:
        output_path = Path(output)
        output_path.write_text(report.model_dump_json(indent=2))
        console.print(f"[green]Report saved to:[/green] {output_path}")
    else:
        _display_analysis_summary(report, verbose)


@app.command()
def check(
    target: str = typer.Argument(
        ..., help="Target platform to check compatibility against."
    ),
    path: str = typer.Option(
        "~/.dotfiles", "--path", "-p", help="Path to the dotfiles directory."
    ),
    source: str = typer.Option(
        None, "--source", "-s", help="Source platform (auto-detected if not specified)."
    ),
    output: str = typer.Option(
        None, "--output", "-o", help="Output file for the compatibility report."
    ),
) -> None:
    """Run compatibility analysis against a target platform."""
    path = Path(path).expanduser()

    if not path.exists():
        console.print(f"[red]Error:[/red] Path not found: {path}")
        raise typer.Exit(1)

    checker = CompatibilityChecker()

    # Auto-detect source platform if not specified
    if not source:
        source = checker.detect_current_platform()
        console.print(f"[dim]Detected source platform: {source}[/dim]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing dotfiles...", total=None)

        analyzer = DotfileAnalyzer(path)
        analyses = analyzer.analyze_all()

        progress.update(task, description="Checking compatibility...")
        issues = checker.check_compatibility(analyses, target, source)

    # Display results
    table = Table(title=f"Compatibility Report: {source} -> {target}")
    table.add_column("Severity", style="cyan")
    table.add_column("Message", style="white")
    table.add_column("Suggestion", style="green")

    for issue in issues:
        severity_style = {
            "info": "blue",
            "warning": "yellow",
            "error": "red",
            "critical": "bold red",
        }.get(issue.severity.value, "white")
        table.add_row(
            f"[{severity_style}]{issue.severity.value.upper()}[/{severity_style}]",
            issue.message,
            issue.suggestion,
        )

    console.print(table)

    if output:
        output_path = Path(output)
        output_path.write_text(
            json.dumps([i.model_dump() for i in issues], indent=2)
        )
        console.print(f"[green]Report saved to:[/green] {output_path}")


@app.command()
def generate(
    target: str = typer.Argument(
        ..., help="Target platform to generate migration script for."
    ),
    path: str = typer.Option(
        "~/.dotfiles", "--path", "-p", help="Path to the dotfiles directory."
    ),
    source: str = typer.Option(
        None, "--source", "-s", help="Source platform (auto-detected if not specified)."
    ),
    output: str = typer.Option(
        "migration.sh", "--output", "-o", help="Output file for the migration script."
    ),
) -> None:
    """Generate migration scripts for a target platform."""
    path = Path(path).expanduser()

    if not path.exists():
        console.print(f"[red]Error:[/red] Path not found: {path}")
        raise typer.Exit(1)

    checker = CompatibilityChecker()
    conflict_detector = ConflictDetector()
    generator = MigrationGenerator()

    # Auto-detect source platform
    if not source:
        source = checker.detect_current_platform()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing dotfiles...", total=None)

        analyzer = DotfileAnalyzer(path)
        analyses = analyzer.analyze_all()

        progress.update(task, description="Generating migration plan...")
        plan = generator.generate_migration_script(
            analyses=analyses,
            target_platform=target,
            source_platform=source,
            compatibility_checker=checker,
            conflict_detector=conflict_detector,
        )

        progress.update(task, description="Rendering migration script...")
        script = generator.render_install_script(plan)

    # Save script
    output_path = Path(output)
    generator.save_script(script, output_path)

    console.print(
        Panel(
            f"[green]Migration script generated successfully![/green]\n\n"
            f"Source: {source}\n"
            f"Target: {target}\n"
            f"Steps: {len(plan.steps)}\n"
            f"Estimated time: {plan.estimated_time}\n"
            f"Output: {output_path}",
            title="Migration Plan Summary",
        )
    )

    if plan.issues:
        console.print(f"\n[yellow]Warning: {len(plan.issues)} compatibility issue(s) detected.[/yellow]")

    if plan.conflicts:
        console.print(f"\n[yellow]Warning: {len(plan.conflicts)} conflict(s) detected.[/yellow]")


@app.command()
def migrate(
    target: str = typer.Argument(
        ..., help="Target platform to migrate to."
    ),
    path: str = typer.Option(
        "~/.dotfiles", "--path", "-p", help="Path to the dotfiles directory."
    ),
    source: str = typer.Option(
        None, "--source", "-s", help="Source platform (auto-detected if not specified)."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Simulate migration without applying changes."
    ),
    output: str = typer.Option(
        None, "--output", "-o", help="Save migration script to file instead of executing."
    ),
) -> None:
    """Apply migration (with optional dry-run)."""
    path = Path(path).expanduser()

    if not path.exists():
        console.print(f"[red]Error:[/red] Path not found: {path}")
        raise typer.Exit(1)

    checker = CompatibilityChecker()
    conflict_detector = ConflictDetector()
    generator = MigrationGenerator()

    # Auto-detect source platform
    if not source:
        source = checker.detect_current_platform()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating migration plan...", total=None)

        analyzer = DotfileAnalyzer(path)
        analyses = analyzer.analyze_all()

        progress.update(task, description="Creating migration plan...")
        plan = generator.generate_migration_script(
            analyses=analyses,
            target_platform=target,
            source_platform=source,
            compatibility_checker=checker,
            conflict_detector=conflict_detector,
        )

        progress.update(task, description="Rendering script...")
        script = generator.render_install_script(plan, dry_run=dry_run)

    if output:
        output_path = Path(output)
        generator.save_script(script, output_path)
        console.print(f"[green]Migration script saved to:[/green] {output_path}")
    else:
        if dry_run:
            console.print(
                Panel(
                    "[yellow]DRY RUN MODE[/yellow]\n\n"
                    "The following commands would be executed:\n\n"
                    f"{script}",
                    title="Migration Preview",
                )
            )
        else:
            console.print(
                Panel(
                    "[red]WARNING: This will apply migration changes to your system.[/red]\n\n"
                    "It is recommended to use --dry-run first to preview changes.\n"
                    "Use --output to save the script and review it manually.",
                    title="Migration Warning",
                )
            )
            if typer.confirm("Do you want to continue?"):
                console.print("[yellow]Migration execution not yet implemented. Use --output to save the script.[/yellow]")


@app.command()
def rollback(
    output: str = typer.Option(
        "rollback.sh", "--output", "-o", help="Output file for the rollback script."
    ),
) -> None:
    """Generate rollback scripts from a previous migration."""
    generator = MigrationGenerator()

    # Create a minimal plan for rollback generation
    from dotsync.models import MigrationPlan

    plan = MigrationPlan(
        source_platform="unknown",
        target_platform="unknown",
        steps=[],
    )

    script = generator.render_rollback_script(plan)
    output_path = Path(output)
    generator.save_script(script, output_path)

    console.print(f"[green]Rollback script saved to:[/green] {output_path}")


@app.command()
def graph(
    path: str = typer.Option(
        "~/.dotfiles", "--path", "-p", help="Path to the dotfiles directory."
    ),
    output: str = typer.Option(
        "deps.mermaid", "--output", "-o", help="Output file for the Mermaid diagram."
    ),
) -> None:
    """Export dependency graph as Mermaid diagram."""
    path = Path(path).expanduser()

    if not path.exists():
        console.print(f"[red]Error:[/red] Path not found: {path}")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing dotfiles...", total=None)

        analyzer = DotfileAnalyzer(path)
        analyses = analyzer.analyze_all()

        progress.update(task, description="Building dependency graph...")
        graph_builder = DependencyGraphBuilder()
        dep_graph = graph_builder.build(analyses)

        mermaid = dep_graph.to_mermaid()

    # Save output
    output_path = Path(output)
    output_path.write_text(mermaid)

    console.print(f"[green]Dependency graph saved to:[/green] {output_path}")
    console.print(f"\n[dim]Total nodes: {len(dep_graph.nodes)}[/dim]")
    console.print(f"[dim]Total edges: {len(dep_graph.edges)}[/dim]")


@app.command()
def conflicts(
    path: str = typer.Option(
        "~/.dotfiles", "--path", "-p", help="Path to the dotfiles directory."
    ),
    output: str = typer.Option(
        None, "--output", "-o", help="Output file for the conflict report."
    ),
) -> None:
    """Detect configuration conflicts."""
    path = Path(path).expanduser()

    if not path.exists():
        console.print(f"[red]Error:[/red] Path not found: {path}")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing dotfiles...", total=None)

        analyzer = DotfileAnalyzer(path)
        analyses = analyzer.analyze_all()

        progress.update(task, description="Detecting conflicts...")
        detector = ConflictDetector()
        conflicts = detector.detect_conflicts(analyses)

    # Display results
    if conflicts:
        table = Table(title="Configuration Conflicts")
        table.add_column("Severity", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Affected", style="yellow")
        table.add_column("Resolution", style="green")

        for conflict in conflicts:
            severity_style = {
                "info": "blue",
                "warning": "yellow",
                "error": "red",
                "critical": "bold red",
            }.get(conflict.severity.value, "white")
            table.add_row(
                f"[{severity_style}]{conflict.severity.value.upper()}[/{severity_style}]",
                conflict.description,
                conflict.affected_variable,
                conflict.resolution,
            )

        console.print(table)
    else:
        console.print("[green]No conflicts detected![/green]")

    if output:
        output_path = Path(output)
        output_path.write_text(
            json.dumps([c.model_dump() for c in conflicts], indent=2)
        )
        console.print(f"[green]Conflict report saved to:[/green] {output_path}")


def _display_analysis_summary(report: AnalysisReport, verbose: bool = False) -> None:
    """Display a summary of the analysis results."""
    console.print(
        Panel(
            f"[bold]DotSync Analysis Report[/bold]\n\n"
            f"Path: {report.source_path}\n"
            f"Files analyzed: {len(report.analyzed_files)}\n"
            f"Total dependencies: {report.total_dependencies}\n"
            f"Conflicts: {len(report.conflicts)}",
            title="Analysis Complete",
        )
    )

    # Files table
    table = Table(title="Analyzed Files")
    table.add_column("File", style="cyan")
    table.add_column("Type", style="white")
    table.add_column("Dependencies", style="yellow")
    table.add_column("Aliases", style="green")

    for analysis in report.analyzed_files:
        table.add_row(
            Path(analysis.path).name,
            analysis.file_type,
            str(len(analysis.dependencies)),
            str(len(analysis.aliases)),
        )

    console.print(table)

    # Conflicts
    if report.conflicts:
        console.print("\n[yellow]Conflicts detected:[/yellow]")
        for conflict in report.conflicts:
            console.print(f"  - [{conflict.severity.value}] {conflict.description}")

    if verbose:
        console.print("\n[dim]Use 'dotsync graph' to visualize the dependency graph.[/dim]")
        console.print("[dim]Use 'dotsync check --target <platform>' to check compatibility.[/dim]")


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
