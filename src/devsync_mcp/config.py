"""Config type detection and file pattern matching."""

import platform
from enum import Enum
from pathlib import Path


class ConfigType(str, Enum):
    """Types of configuration files that can be synced."""

    SHELL_PROFILE = "shell_profile"
    GIT_CONFIG = "git_config"
    EDITOR_CONFIG = "editor_config"
    AI_RULES = "ai_rules"
    VSCODE_SETTINGS = "vscode_settings"
    SSH_CONFIG = "ssh_config"
    CUSTOM = "custom"


CONFIG_PATTERNS: dict[ConfigType, list[str]] = {
    ConfigType.SHELL_PROFILE: [
        ".zshrc",
        ".bashrc",
        ".bash_profile",
        ".profile",
        ".zprofile",
        ".zshenv",
    ],
    ConfigType.GIT_CONFIG: [
        ".gitconfig",
        ".gitignore_global",
        ".gitmessage",
    ],
    ConfigType.EDITOR_CONFIG: [
        ".editorconfig",
    ],
    ConfigType.AI_RULES: [
        "CLAUDE.md",
        ".cursorrules",
        ".cursor/rules/",
        ".claude/rules/",
        ".windsurfrules",
        ".windsurf/rules/",
        ".clinerules/",
        ".roo/rules/",
        "AGENTS.md",
        ".github/instructions/",
        ".kiro/steering/",
    ],
    ConfigType.VSCODE_SETTINGS: [
        ".vscode/settings.json",
        ".vscode/extensions.json",
        ".vscode/launch.json",
        ".vscode/tasks.json",
    ],
    ConfigType.SSH_CONFIG: [
        ".ssh/config",
    ],
}

HOME_BASED_TYPES = {
    ConfigType.SHELL_PROFILE,
    ConfigType.GIT_CONFIG,
    ConfigType.SSH_CONFIG,
}

PROJECT_BASED_TYPES = {
    ConfigType.AI_RULES,
    ConfigType.EDITOR_CONFIG,
    ConfigType.VSCODE_SETTINGS,
}


def detect_config_type(filename: str) -> ConfigType:
    """Detect the config type from a filename or path."""
    name = Path(filename).name
    full = filename

    for config_type, patterns in CONFIG_PATTERNS.items():
        for pattern in patterns:
            if name == pattern or full.endswith(pattern.rstrip("/")):
                return config_type

    return ConfigType.CUSTOM


def get_default_target(config_name: str, config_type: ConfigType) -> str:
    """Get the default target path for a config type.

    Returns a path string. Home-based configs use ~ prefix.
    Project-based configs are relative to project root.
    """
    if config_type in HOME_BASED_TYPES:
        return f"~/{config_name}"
    return config_name


def expand_target_path(target: str, project_root: Path | None = None) -> Path:
    """Expand a target path to an absolute path.

    Handles ~ expansion and project-relative paths.
    """
    if target.startswith("~"):
        return Path(target).expanduser()
    if project_root:
        return project_root / target
    return Path.cwd() / target


def is_platform_relevant(config_type: ConfigType) -> bool:
    """Check if a config type is relevant on the current platform."""
    system = platform.system()
    if config_type == ConfigType.SHELL_PROFILE and system == "Windows":
        return False
    return True
