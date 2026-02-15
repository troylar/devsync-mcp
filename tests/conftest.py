"""Shared test fixtures."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory that's cleaned up after the test."""
    with tempfile.TemporaryDirectory(prefix="devsync_mcp_test_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_profile_dir(temp_dir: Path) -> Path:
    """Create a sample team profile directory with manifest and config files."""
    profile_dir = temp_dir / "profiles" / "acme-team"
    profile_dir.mkdir(parents=True)

    manifest = profile_dir / "devsync-profile.yaml"
    manifest.write_text(
        """name: acme-team-config
description: ACME Corp standard dev environment
version: 1.0.0

configs:
  - name: zshrc-additions
    file: shell/zshrc-additions.sh
    target: ~/.zshrc
    type: shell_profile
    description: Team shell aliases and PATH additions

  - name: claude-rules
    file: ai-rules/claude-rules.md
    target: CLAUDE.md
    type: ai_rules
    description: Team coding standards for Claude Code

  - name: editorconfig
    file: editor/.editorconfig
    target: .editorconfig
    type: editor_config
    description: Standard editor configuration
""",
        encoding="utf-8",
    )

    shell_dir = profile_dir / "shell"
    shell_dir.mkdir()
    (shell_dir / "zshrc-additions.sh").write_text(
        """# ACME Team Shell Config
export ACME_ENV=production
alias acme-deploy='acme-cli deploy --env $ACME_ENV'
alias acme-logs='acme-cli logs --tail 100'
export PATH="$HOME/.acme/bin:$PATH"
""",
        encoding="utf-8",
    )

    ai_dir = profile_dir / "ai-rules"
    ai_dir.mkdir()
    (ai_dir / "claude-rules.md").write_text(
        """# ACME Team Coding Standards

## Code Style
- Use 4 spaces for indentation
- Maximum line length: 120 characters
- Use type hints for all function signatures

## Testing
- Minimum 80% code coverage
- Use pytest for all tests
""",
        encoding="utf-8",
    )

    editor_dir = profile_dir / "editor"
    editor_dir.mkdir()
    (editor_dir / ".editorconfig").write_text(
        """root = true

[*]
indent_style = space
indent_size = 4
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true
""",
        encoding="utf-8",
    )

    return profile_dir


@pytest.fixture
def sample_home_dir(temp_dir: Path) -> Path:
    """Create a simulated home directory with existing config files."""
    home = temp_dir / "home"
    home.mkdir()

    (home / ".zshrc").write_text(
        """# My personal zshrc
export EDITOR=vim
alias ll='ls -la'
alias gs='git status'

# Custom PATH
export PATH="$HOME/bin:$PATH"
""",
        encoding="utf-8",
    )

    (home / ".gitconfig").write_text(
        """[user]
    name = Test User
    email = test@example.com
[alias]
    co = checkout
    br = branch
""",
        encoding="utf-8",
    )

    return home
