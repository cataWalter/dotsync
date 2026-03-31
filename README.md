# DotSync - Intelligent Dotfile Migration & Compatibility Analyzer

DotSync is a CLI tool that analyzes your dotfiles and generates compatibility reports for cross-platform migration. It maps dependencies between configurations, detects conflicts, and automatically generates migration scripts tailored to the target platform.

## The Problem

When you switch machines or operating systems, you don't know which configurations will work, which will break something, and which dependencies are missing. Existing tools like `chezmoi`, `stow`, and `dotbot` only handle symlinks and declarative installation. None of them perform static analysis of dependencies and cross-platform compatibility.

## What DotSync Does

1. **Analyzes** your dotfiles and generates a compatibility report for different platforms (macOS → Linux, Intel → Apple Silicon, etc.)
2. **Maps dependencies** between configurations (e.g., `.zshrc` requires `starship`, which requires `brew`)
3. **Generates migration scripts** automatically, adapted to the target platform
4. **Detects conflicts** between configurations of different tools (e.g., two tools modifying the same environment variable)

## Features

- **Dependency Graph Visualization** - Generates a Mermaid graph of dependencies between dotfiles
- **Dry-run Mode** - Simulates migration without applying changes
- **Rollback Generation** - Generates automatic rollback scripts
- **Platform Matrix** - Tests compatibility across multiple platforms via GitHub Actions
- **Conflict Detection** - Identifies overlapping or conflicting configurations
- **AST-based Parsing** - Uses abstract syntax tree analysis for accurate dependency extraction

## Recommended Tech Stack

### Core
- **Python 3.11+** - Primary language for the CLI tool
- **Typer** - Modern CLI framework with automatic help generation and type hints
- **Rich** - Beautiful terminal output for reports and progress indicators

### Analysis Engine
- **tree-sitter** - Incremental parsing library for analyzing shell scripts, gitconfig, TOML, etc.
- **networkx** - Graph library for building and analyzing dependency graphs
- **pydantic** - Data validation using Python type hints

### Output & Reporting
- **Jinja2** - Template engine for generating migration scripts
- **Mermaid CLI** - Generates visual dependency graphs from DOT files
- **PyYAML** - YAML support for configuration files and platform definitions

### Testing & CI
- **pytest** - Testing framework with coverage reporting
- **GitHub Actions** - CI/CD for automated testing and cross-platform validation
- **pre-commit** - Git hooks for code quality (black, ruff, mypy)

### Packaging
- **uv** - Fast Python package manager and resolver
- **hatch** - Modern Python project manager for building and publishing

## Project Structure

```
dotsync/
├── pyproject.toml              # Project metadata and dependencies
├── README.md                   # This file
├── src/
│   └── dotsync/
│       ├── __init__.py
│       ├── cli.py              # CLI entry point with Typer
│       ├── analyzer.py         # AST parsing of dotfiles
│       ├── dependency_graph.py # Dependency graph builder
│       ├── compatibility.py    # Cross-platform compatibility checks
│       ├── generator.py        # Migration script generator
│       ├── conflict_detector.py # Conflict detection engine
│       └── models.py           # Pydantic data models
├── tests/
│   ├── test_analyzer.py
│   ├── test_dependency_graph.py
│   ├── test_compatibility.py
│   └── fixtures/               # Sample dotfiles for testing
├── platforms/                  # Platform compatibility database
│   ├── macos.json
│   ├── linux-ubuntu.json
│   ├── linux-arch.json
│   └── linux-fedora.json
├── templates/                  # Jinja2 templates for migration scripts
│   ├── install.sh.j2
│   ├── rollback.sh.j2
│   └── report.md.j2
└── .github/
    └── workflows/
        └── ci.yml              # GitHub Actions CI pipeline
```

## Quick Start

### Prerequisites

- Python 3.11+
- uv (recommended) or pip

### Installation

```bash
# Clone the repository
git clone https://github.com/cataWalter/dotsync.git
cd dotsync

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Usage

```bash
# Analyze dotfiles in your home directory
dotsync analyze ~/.dotfiles

# Generate compatibility report for Ubuntu
dotsync check --target linux-ubuntu

# Generate migration script
dotsync generate --target linux-ubuntu --output migration.sh

# Dry-run migration
dotsync migrate --target linux-ubuntu --dry-run

# Generate rollback script
dotsync rollback --output rollback.sh

# Visualize dependency graph
dotsync graph --output deps.mermaid
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `analyze` | Parse dotfiles and extract dependencies |
| `check` | Run compatibility analysis against a target platform |
| `generate` | Create migration scripts for a target platform |
| `migrate` | Apply migration (with optional dry-run) |
| `rollback` | Generate rollback scripts from a previous migration |
| `graph` | Export dependency graph as Mermaid diagram |
| `conflicts` | Detect configuration conflicts |

## Supported Dotfiles

- `.zshrc` / `.bashrc` - Shell configurations
- `.gitconfig` - Git settings
- `.config/starship.toml` - Starship prompt config
- `.config/aerospace/.aerospace.toml` - Window manager config
- `.config/ghostty/config` - Terminal config
- `.config/karabiner/karabiner.json` - Key remapping config
- `.config/gh/config.yml` - GitHub CLI config
- `.config/vscode/settings.json` - VS Code settings

## Platform Support

| Platform | Status |
|----------|--------|
| macOS (Apple Silicon) | ✅ Supported |
| macOS (Intel) | ✅ Supported |
| Ubuntu 22.04/24.04 | ✅ Supported |
| Arch Linux | ✅ Supported |
| Fedora | ✅ Supported |
| NixOS | 🚧 Planned |
| Windows (WSL2) | 🚧 Planned |

## Development

### Running Tests

```bash
pytest --cov=dotsync --cov-report=term-missing
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type checking
mypy src/
```

### Adding New Platform Support

Add a JSON file in `platforms/` with the following structure:

```json
{
  "name": "linux-ubuntu",
  "package_manager": "apt",
  "shell_default": "/bin/bash",
  "config_paths": {
    "zshrc": "~/.zshrc",
    "gitconfig": "~/.gitconfig"
  },
  "package_map": {
    "starship": "starship",
    "fzf": "fzf",
    "ripgrep": "ripgrep"
  },
  "incompatible_tools": ["brew", "mas"]
}
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please read the contributing guidelines and open issues for feature requests or bugs.
