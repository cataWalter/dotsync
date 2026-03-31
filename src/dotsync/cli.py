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


@app.command()
def export_report(
    path: str = typer.Option(
        "~/.dotfiles", "--path", "-p", help="Path to the dotfiles directory."
    ),
    output: str = typer.Option(
        None, "--output", "-o", help="Output file for the report."
    ),
    format: str = typer.Option(
        "json", "--format", "-f", help="Output format: json, yaml, or markdown."
    ),
) -> None:
    """Export analysis report in various formats (JSON, YAML, Markdown)."""
    import json as json_module

    try:
        import yaml
    except ImportError:
        yaml = None  # type: ignore

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

        progress.update(task, description="Building report...")
        graph_builder = DependencyGraphBuilder()
        dep_graph = graph_builder.build(analyses)

        conflict_detector = ConflictDetector()
        conflicts = conflict_detector.detect_conflicts(analyses)

    total_deps = sum(len(a.dependencies) for a in analyses)

    report = AnalysisReport(
        source_path=str(path),
        analyzed_files=analyses,
        dependency_graph=dep_graph,
        total_dependencies=total_deps,
        total_issues=len(conflicts),
        conflicts=conflicts,
    )

    # Generate output based on format
    if format == "json":
        content = report.model_dump_json(indent=2)
    elif format == "yaml":
        if yaml is None:
            console.print("[red]Error:[/red] PyYAML is required for YAML export")
            raise typer.Exit(1)
        content = yaml.dump(report.model_dump(), default_flow_style=False, sort_keys=False)
    elif format == "markdown":
        checker = CompatibilityChecker()
        generator = MigrationGenerator()
        content = generator.render_report(report, "linux-ubuntu")
    else:
        console.print(f"[red]Error:[/red] Unknown format: {format}")
        raise typer.Exit(1)

    if output:
        output_path = Path(output)
        output_path.write_text(content)
        console.print(f"[green]Report exported to:[/green] {output_path}")
    else:
        console.print(content)


@app.command()
def validate(
    path: str = typer.Option(
        "~/.dotfiles", "--path", "-p", help="Path to the dotfiles directory."
    ),
    strict: bool = typer.Option(
        False, "--strict", help="Fail on warnings as well as errors."
    ),
) -> None:
    """Validate dotfiles for common issues and best practices."""
    path = Path(path).expanduser()

    if not path.exists():
        console.print(f"[red]Error:[/red] Path not found: {path}")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Validating dotfiles...", total=None)

        analyzer = DotfileAnalyzer(path)
        analyses = analyzer.analyze_all()

        progress.update(task, description="Running validation checks...")

    issues: list[dict] = []

    for analysis in analyses:
        # Check for empty files
        if not analysis.raw_content.strip():
            issues.append({
                "file": analysis.path,
                "severity": "warning",
                "message": "File is empty",
            })

        # Check for syntax errors
        for error in analysis.parse_errors:
            issues.append({
                "file": analysis.path,
                "severity": "error",
                "message": f"Parse error: {error}",
            })

        # Check for hardcoded paths
        hardcoded_paths = [
            "/usr/local/bin",
            "/opt/homebrew",
            "/home/",
            "C:\\",
        ]
        for line_num, line in enumerate(analysis.raw_content.split("\n"), 1):
            for hp in hardcoded_paths:
                if hp in line and not line.strip().startswith("#"):
                    issues.append({
                        "file": analysis.path,
                        "severity": "warning",
                        "message": f"Line {line_num}: Hardcoded path '{hp}' detected",
                    })

        # Check for deprecated commands
        deprecated = {
            "source ~/.bashrc": "Use 'source' or '.' consistently",
            "export PATH=": "Consider using path management tools like zoxide",
        }
        for deprecated_cmd, suggestion in deprecated.items():
            if deprecated_cmd in analysis.raw_content:
                issues.append({
                    "file": analysis.path,
                    "severity": "info",
                    "message": f"Suggestion: {suggestion}",
                })

        # Check for missing shebang in shell scripts
        if analysis.file_type in ("bash", "zsh", "sh"):
            if not analysis.raw_content.startswith("#!") and not analysis.raw_content.startswith("#"):
                issues.append({
                    "file": analysis.path,
                    "severity": "info",
                    "message": "Consider adding a shebang line for shell scripts",
                })

    # Display results
    table = Table(title="Validation Results")
    table.add_column("Severity", style="cyan")
    table.add_column("File", style="white")
    table.add_column("Message", style="yellow")

    for issue in issues:
        severity_style = {
            "info": "blue",
            "warning": "yellow",
            "error": "red",
        }.get(issue["severity"], "white")
        table.add_row(
            f"[{severity_style}]{issue['severity'].upper()}[/{severity_style}]",
            Path(issue["file"]).name,
            issue["message"],
        )

    if issues:
        console.print(table)
    else:
        console.print("[green]All dotfiles passed validation![/green]")

    # Summary
    errors = sum(1 for i in issues if i["severity"] == "error")
    warnings = sum(1 for i in issues if i["severity"] == "warning")
    infos = sum(1 for i in issues if i["severity"] == "info")

    console.print(f"\n[dim]Errors: {errors}, Warnings: {warnings}, Info: {infos}[/dim]")

    if strict and (errors > 0 or warnings > 0):
        raise typer.Exit(1)
    elif errors > 0:
        raise typer.Exit(1)


@app.command()
def diff(
    path_a: str = typer.Argument(..., help="Path to the first dotfiles directory."),
    path_b: str = typer.Argument(..., help="Path to the second dotfiles directory."),
    output: str = typer.Option(
        None, "--output", "-o", help="Output file for the diff report."
    ),
) -> None:
    """Compare two dotfiles directories and show differences."""
    path_a = Path(path_a).expanduser()
    path_b = Path(path_b).expanduser()

    if not path_a.exists():
        console.print(f"[red]Error:[/red] Path not found: {path_a}")
        raise typer.Exit(1)
    if not path_b.exists():
        console.print(f"[red]Error:[/red] Path not found: {path_b}")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing directories...", total=None)

        analyzer_a = DotfileAnalyzer(path_a)
        analyses_a = analyzer_a.analyze_all()

        analyzer_b = DotfileAnalyzer(path_b)
        analyses_b = analyzer_b.analyze_all()

        progress.update(task, description="Comparing configurations...")

    # Build comparison maps
    def build_comparison_map(analyses: list) -> dict:
        result = {}
        for analysis in analyses:
            name = Path(analysis.path).name
            result[name] = analysis
        return result

    map_a = build_comparison_map(analyses_a)
    map_b = build_comparison_map(analyses_b)

    all_files = set(map_a.keys()) | set(map_b.keys())

    # Comparison results
    table = Table(title=f"Dotfiles Comparison: {path_a.name} vs {path_b.name}")
    table.add_column("File", style="cyan")
    table.add_column(f"{path_a.name}", style="green")
    table.add_column(f"{path_b.name}", style="yellow")
    table.add_column("Differences", style="red")

    differences: list[dict] = []

    for filename in sorted(all_files):
        in_a = filename in map_a
        in_b = filename in map_b

        if in_a and in_b:
            a = map_a[filename]
            b = map_b[filename]

            diffs = []
            if len(a.dependencies) != len(b.dependencies):
                diffs.append(f"Dependencies: {len(a.dependencies)} vs {len(b.dependencies)}")
            if len(a.aliases) != len(b.aliases):
                diffs.append(f"Aliases: {len(a.aliases)} vs {len(b.aliases)}")
            if len(a.functions) != len(b.functions):
                diffs.append(f"Functions: {len(a.functions)} vs {len(b.functions)}")

            # Check for different env vars
            a_env_keys = set(a.environment_variables.keys())
            b_env_keys = set(b.environment_variables.keys())
            added_vars = a_env_keys - b_env_keys
            removed_vars = b_env_keys - a_env_keys
            if added_vars or removed_vars:
                if added_vars:
                    diffs.append(f"Added vars: {', '.join(added_vars)}")
                if removed_vars:
                    diffs.append(f"Removed vars: {', '.join(removed_vars)}")

            diff_str = "; ".join(diffs) if diffs else "None"
            table.add_row(
                filename,
                f"{len(a.dependencies)} deps, {len(a.aliases)} aliases",
                f"{len(b.dependencies)} deps, {len(b.aliases)} aliases",
                diff_str,
            )

            if diffs:
                differences.append({
                    "file": filename,
                    "differences": diffs,
                })
        elif in_a:
            table.add_row(
                filename,
                f"{len(map_a[filename].dependencies)} deps",
                "[dim]Not present[/dim]",
                "Only in A",
            )
            differences.append({
                "file": filename,
                "differences": ["Only present in first directory"],
            })
        else:
            table.add_row(
                filename,
                "[dim]Not present[/dim]",
                f"{len(map_b[filename].dependencies)} deps",
                "Only in B",
            )
            differences.append({
                "file": filename,
                "differences": ["Only present in second directory"],
            })

    console.print(table)

    # Summary
    console.print(f"\n[dim]Total files compared: {len(all_files)}[/dim]")
    console.print(f"[dim]Files with differences: {len(differences)}[/dim]")

    if output:
        output_path = Path(output)
        output_path.write_text(
            json.dumps(differences, indent=2)
        )
        console.print(f"[green]Diff report saved to:[/green] {output_path}")


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
