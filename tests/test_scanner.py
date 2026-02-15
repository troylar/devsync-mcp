"""Tests for environment scanner."""

from pathlib import Path

from devsync_mcp.config import ConfigType
from devsync_mcp.scanner import EnvironmentScanner


class TestEnvironmentScanner:
    def test_scan_for_existing_target(self, temp_dir: Path) -> None:
        test_file = temp_dir / ".editorconfig"
        test_file.write_text("root = true\n", encoding="utf-8")

        scanner = EnvironmentScanner(project_root=temp_dir)
        result = scanner.scan_for_target(".editorconfig")
        assert result is not None
        assert result.exists is True
        assert result.size > 0
        assert result.checksum != ""

    def test_scan_for_missing_target(self, temp_dir: Path) -> None:
        scanner = EnvironmentScanner(project_root=temp_dir)
        result = scanner.scan_for_target("nonexistent.txt")
        assert result is not None
        assert result.exists is False

    def test_scan_all_finds_project_configs(self, temp_dir: Path) -> None:
        (temp_dir / ".editorconfig").write_text("root = true\n", encoding="utf-8")
        (temp_dir / "CLAUDE.md").write_text("# Rules\n", encoding="utf-8")

        scanner = EnvironmentScanner(project_root=temp_dir)
        detected = scanner.scan_all()

        paths = [d.path for d in detected]
        assert any(".editorconfig" in p for p in paths)
        assert any("CLAUDE.md" in p for p in paths)

    def test_detected_config_to_dict(self, temp_dir: Path) -> None:
        test_file = temp_dir / ".editorconfig"
        test_file.write_text("root = true\n", encoding="utf-8")

        scanner = EnvironmentScanner(project_root=temp_dir)
        result = scanner.scan_for_target(".editorconfig")
        assert result is not None

        d = result.to_dict()
        assert "path" in d
        assert "type" in d
        assert "exists" in d
        assert d["exists"] is True
