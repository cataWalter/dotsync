"""Git integration for dotfiles repository management."""

from __future__ import annotations

import subprocess
from pathlib import Path


class GitIntegration:
    """Manages git operations for dotfiles repositories."""

    def __init__(self, dotfiles_path: str | Path):
        self.dotfiles_path = Path(dotfiles_path)

    def is_git_repo(self) -> bool:
        """Check if the dotfiles directory is a git repository."""
        git_dir = self.dotfiles_path / ".git"
        return git_dir.exists() or self._run_git("rev-parse", "--git-dir", check=False) is not None

    def init_repo(self, remote_url: str | None = None) -> bool:
        """Initialize a git repository for dotfiles."""
        if self.is_git_repo():
            return False

        self._run_git("init")
        self._run_git("add", ".")
        self._run_git("commit", "-m", "Initial dotfiles commit")

        if remote_url:
            self._run_git("remote", "add", "origin", remote_url)

        return True

    def add_dotfiles(self, files: list[str] | None = None) -> list[str]:
        """Add dotfiles to the git repository."""
        if not self.is_git_repo():
            return []

        if files:
            for f in files:
                self._run_git("add", f)
        else:
            self._run_git("add", ".")

        return self.get_status()

    def commit(self, message: str) -> bool:
        """Commit changes to the git repository."""
        if not self.is_git_repo():
            return False

        result = self._run_git("commit", "-m", message)
        return result is not None

    def push(self, remote: str = "origin", branch: str = "main") -> bool:
        """Push changes to remote repository."""
        if not self.is_git_repo():
            return False

        result = self._run_git("push", remote, branch)
        return result is not None

    def pull(self, remote: str = "origin", branch: str = "main") -> bool:
        """Pull changes from remote repository."""
        if not self.is_git_repo():
            return False

        result = self._run_git("pull", remote, branch)
        return result is not None

    def get_status(self) -> list[str]:
        """Get git status of the dotfiles directory."""
        if not self.is_git_repo():
            return []

        result = self._run_git("status", "--porcelain")
        if result:
            return result.strip().split("\n")
        return []

    def get_log(self, limit: int = 10) -> list[str]:
        """Get git log entries."""
        if not self.is_git_repo():
            return []

        result = self._run_git("log", f"--oneline", f"-{limit}")
        if result:
            return result.strip().split("\n")
        return []

    def get_remote_url(self) -> str | None:
        """Get the remote repository URL."""
        if not self.is_git_repo():
            return None

        result = self._run_git("remote", "get-url", "origin")
        return result.strip() if result else None

    def create_branch(self, name: str) -> bool:
        """Create a new git branch."""
        if not self.is_git_repo():
            return False

        self._run_git("branch", name)
        return True

    def checkout_branch(self, name: str) -> bool:
        """Checkout a git branch."""
        if not self.is_git_repo():
            return False

        result = self._run_git("checkout", name)
        return result is not None

    def get_current_branch(self) -> str | None:
        """Get the current git branch."""
        if not self.is_git_repo():
            return None

        result = self._run_git("branch", "--show-current")
        return result.strip() if result else None

    def _run_git(self, *args: str, check: bool = True) -> str | None:
        """Run a git command in the dotfiles directory."""
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.dotfiles_path,
                capture_output=True,
                text=True,
                check=check,
            )
            return result.stdout
        except subprocess.CalledProcessError:
            return None
