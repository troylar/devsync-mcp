"""Tests for MCP server tool implementation functions."""

from pathlib import Path

from devsync_mcp import server
from devsync_mcp.backup import BackupManager
from devsync_mcp.merger import MergeOrchestrator
from devsync_mcp.profile import ProfileManager
from devsync_mcp.tracker import MergeTracker


def _setup_server(temp_dir: Path, profile_dir: Path) -> None:
    """Wire up server globals with test paths."""
    pm = ProfileManager(profiles_dir=profile_dir.parent)
    tracker = MergeTracker(merges_path=temp_dir / "merges.json")
    backup = BackupManager(backup_dir=temp_dir / "backups")
    orch = MergeOrchestrator(profile_manager=pm, tracker=tracker, backup_manager=backup)

    server._profile_manager = pm
    server._tracker = tracker
    server._backup_manager = backup
    server._orchestrator = orch


class TestListProfileConfigs:
    def test_returns_configs(self, temp_dir: Path, sample_profile_dir: Path) -> None:
        _setup_server(temp_dir, sample_profile_dir)
        namespace = sample_profile_dir.name

        result = server._list_profile_configs(namespace)

        assert result["status"] == "ok"
        assert len(result["configs"]) == 3
        names = [c["name"] for c in result["configs"]]
        assert "zshrc-additions" in names
        assert "claude-rules" in names
        assert "editorconfig" in names

    def test_missing_profile(self, temp_dir: Path, sample_profile_dir: Path) -> None:
        _setup_server(temp_dir, sample_profile_dir)

        result = server._list_profile_configs("nonexistent")

        assert result["status"] == "error"


class TestDetectCurrentConfigs:
    def test_detects_existing_files(self, temp_dir: Path, sample_profile_dir: Path) -> None:
        _setup_server(temp_dir, sample_profile_dir)
        (temp_dir / ".editorconfig").write_text("root = true\n", encoding="utf-8")

        result = server._detect_current_configs(project_root=str(temp_dir))

        assert result["status"] == "ok"
        assert result["total"] > 0


class TestPreviewMerge:
    def test_preview_returns_content(self, temp_dir: Path, sample_profile_dir: Path) -> None:
        _setup_server(temp_dir, sample_profile_dir)
        namespace = sample_profile_dir.name

        result = server._preview_merge(namespace, "editorconfig", project_root=str(temp_dir))

        assert result["status"] == "ok"
        assert "root = true" in result["source_content"]
        assert result["target_content"] is None

    def test_preview_missing_config(self, temp_dir: Path, sample_profile_dir: Path) -> None:
        _setup_server(temp_dir, sample_profile_dir)
        namespace = sample_profile_dir.name

        result = server._preview_merge(namespace, "nonexistent")

        assert result["status"] == "error"


class TestApplyMerge:
    def test_apply_writes_file(self, temp_dir: Path, sample_profile_dir: Path) -> None:
        _setup_server(temp_dir, sample_profile_dir)
        namespace = sample_profile_dir.name
        target = str(temp_dir / ".editorconfig")
        merged = "root = true\nindent_size = 4\n"

        result = server._apply_merge(namespace, "editorconfig", merged, target)

        assert result["status"] == "ok"
        assert Path(target).read_text(encoding="utf-8") == merged


class TestGetMergeStatus:
    def test_all_pending(self, temp_dir: Path, sample_profile_dir: Path) -> None:
        _setup_server(temp_dir, sample_profile_dir)
        namespace = sample_profile_dir.name

        result = server._get_merge_status(namespace, project_root=str(temp_dir))

        assert result["status"] == "ok"
        assert all(c["status"] == "pending" for c in result["configs"])


class TestListBackups:
    def test_empty_backups(self, temp_dir: Path, sample_profile_dir: Path) -> None:
        _setup_server(temp_dir, sample_profile_dir)

        result = server._list_backups()

        assert result["status"] == "ok"
        assert result["total"] == 0


class TestRestoreBackup:
    def test_restore_missing_backup(self, temp_dir: Path, sample_profile_dir: Path) -> None:
        _setup_server(temp_dir, sample_profile_dir)

        result = server._restore_backup("/nonexistent/backup", str(temp_dir / "target"))

        assert result["status"] == "error"
