"""Tests for config type detection."""

from pathlib import Path

from devsync_mcp.config import (
    ConfigType,
    detect_config_type,
    expand_target_path,
    get_default_target,
    is_platform_relevant,
)


class TestDetectConfigType:
    def test_shell_profiles(self) -> None:
        assert detect_config_type(".zshrc") == ConfigType.SHELL_PROFILE
        assert detect_config_type(".bashrc") == ConfigType.SHELL_PROFILE
        assert detect_config_type(".bash_profile") == ConfigType.SHELL_PROFILE
        assert detect_config_type(".profile") == ConfigType.SHELL_PROFILE

    def test_git_configs(self) -> None:
        assert detect_config_type(".gitconfig") == ConfigType.GIT_CONFIG
        assert detect_config_type(".gitignore_global") == ConfigType.GIT_CONFIG

    def test_editor_config(self) -> None:
        assert detect_config_type(".editorconfig") == ConfigType.EDITOR_CONFIG

    def test_ai_rules(self) -> None:
        assert detect_config_type("CLAUDE.md") == ConfigType.AI_RULES
        assert detect_config_type(".cursorrules") == ConfigType.AI_RULES
        assert detect_config_type("AGENTS.md") == ConfigType.AI_RULES

    def test_vscode_settings(self) -> None:
        assert detect_config_type(".vscode/settings.json") == ConfigType.VSCODE_SETTINGS

    def test_unknown_returns_custom(self) -> None:
        assert detect_config_type("random.txt") == ConfigType.CUSTOM
        assert detect_config_type("Dockerfile") == ConfigType.CUSTOM


class TestGetDefaultTarget:
    def test_home_based(self) -> None:
        target = get_default_target(".zshrc", ConfigType.SHELL_PROFILE)
        assert target == "~/.zshrc"

    def test_project_based(self) -> None:
        target = get_default_target("CLAUDE.md", ConfigType.AI_RULES)
        assert target == "CLAUDE.md"


class TestExpandTargetPath:
    def test_tilde_expansion(self) -> None:
        result = expand_target_path("~/.zshrc")
        assert result == Path.home() / ".zshrc"

    def test_project_relative(self, tmp_path: Path) -> None:
        result = expand_target_path("CLAUDE.md", tmp_path)
        assert result == tmp_path / "CLAUDE.md"

    def test_project_relative_no_root(self) -> None:
        result = expand_target_path("CLAUDE.md")
        assert result == Path.cwd() / "CLAUDE.md"


class TestIsPlatformRelevant:
    def test_editor_config_always_relevant(self) -> None:
        assert is_platform_relevant(ConfigType.EDITOR_CONFIG) is True

    def test_ai_rules_always_relevant(self) -> None:
        assert is_platform_relevant(ConfigType.AI_RULES) is True
