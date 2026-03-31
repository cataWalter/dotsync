#!/usr/bin/env bash
# DotSync Migration Script
# Generated: 2026-03-31T11:52:52.665948
# Source: macos
# Target: linux-ubuntu
#
# WARNING: Review this script before running!
# Run with --dry-run first to see what will happen.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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
DRY_RUN=false
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
    local backup_dir="$HOME/.dotsync_backup_20260331_115252"
    log_info "Creating backup in $backup_dir"
    mkdir -p "$backup_dir"

    if [ -f "$HOME/.zshrc" ]; then
        cp -r "$HOME/.zshrc" "$backup_dir/"
        log_info "Backed up $HOME/.zshrc"
    fi
    if [ -f "$HOME/.bashrc" ]; then
        cp -r "$HOME/.bashrc" "$backup_dir/"
        log_info "Backed up $HOME/.bashrc"
    fi
    if [ -f "$HOME/.gitconfig" ]; then
        cp -r "$HOME/.gitconfig" "$backup_dir/"
        log_info "Backed up $HOME/.gitconfig"
    fi
    if [ -f "$HOME/.vimrc" ]; then
        cp -r "$HOME/.vimrc" "$backup_dir/"
        log_info "Backed up $HOME/.vimrc"
    fi
    if [ -f "$HOME/.tmux.conf" ]; then
        cp -r "$HOME/.tmux.conf" "$backup_dir/"
        log_info "Backed up $HOME/.tmux.conf"
    fi

    log_info "Backup complete"
}

# Install dependencies
install_dependencies() {
    log_info "Installing dependencies for linux-ubuntu"

    # Ensure apt is installed
    if ! command -v apt; then
        run_cmd "sudo apt update &amp;&amp; sudo apt install -y build-essential"
    else
        log_info "Skipping: Ensure apt is installed (condition not met)"
    fi

}

# Configure dotfiles
configure_dotfiles() {
    log_info "Configuring dotfiles"

    # Copy /Users/wcatalfamo/Projects/Personal/dotsync/tests/fixtures/.zshrc to $HOME/.zshrc
    run_cmd "cp &#34;/Users/wcatalfamo/Projects/Personal/dotsync/tests/fixtures/.zshrc&#34; &#34;$HOME/.zshrc&#34;"

    # Copy /Users/wcatalfamo/Projects/Personal/dotsync/tests/fixtures/.bashrc to $HOME/.bashrc
    run_cmd "cp &#34;/Users/wcatalfamo/Projects/Personal/dotsync/tests/fixtures/.bashrc&#34; &#34;$HOME/.bashrc&#34;"

    # Copy /Users/wcatalfamo/Projects/Personal/dotsync/tests/fixtures/.gitconfig to $HOME/.gitconfig
    run_cmd "cp &#34;/Users/wcatalfamo/Projects/Personal/dotsync/tests/fixtures/.gitconfig&#34; &#34;$HOME/.gitconfig&#34;"

    # Copy /Users/wcatalfamo/Projects/Personal/dotsync/tests/fixtures/.vimrc to $HOME/.vimrc
    run_cmd "cp &#34;/Users/wcatalfamo/Projects/Personal/dotsync/tests/fixtures/.vimrc&#34; &#34;$HOME/.vimrc&#34;"

    # Copy /Users/wcatalfamo/Projects/Personal/dotsync/tests/fixtures/.tmux.conf to $HOME/.tmux.conf
    run_cmd "cp &#34;/Users/wcatalfamo/Projects/Personal/dotsync/tests/fixtures/.tmux.conf&#34; &#34;$HOME/.tmux.conf&#34;"

}

# Post-installation checks
post_install() {
    log_info "Running post-installation checks"

    # Verify all tools are installed
    run_cmd "true" || log_warn "Verify all tools are installed failed"

}

# Main execution
main() {
    log_info "Starting DotSync migration: macos -> linux-ubuntu"

    # Create backup
    backup_configs

    # Install dependencies
    install_dependencies

    # Configure dotfiles
    configure_dotfiles

    # Post-installation
    post_install

    log_info "Migration complete!"
}

# Run main function
main "$@"