"""Tests for merge orchestration."""

from pathlib import Path

from devsync_mcp.backup import BackupManager
from devsync_mcp.merger import MergeOrchestrator
from devsync_mcp.models import MergeStatus
from devsync_mcp.profile import ProfileManager
from devsync_mcp.tracker import MergeTracker


class TestMergeOrchestrator:
    def _make_orchestrator(self, temp_dir: Path, profile_dir: Path) -> MergeOrchestrator:
        pm = ProfileManager(profiles_dir=profile_dir.parent)
        tracker = MergeTracker(merges_path=temp_dir / "merges.json")
        backup = BackupManager(backup_dir=temp_dir / "backups")
        return MergeOrchestrator(profile_manager=pm, tracker=tracker, backup_manager=backup)

    def test_preview_merge_with_no_existing_target(self, temp_dir: Path, sample_profile_dir: Path) -> None:
        orch = self._make_orchestrator(temp_dir, sample_profile_dir)
        namespace = sample_profile_dir.name

        preview = orch.preview_merge(namespace, "editorconfig", project_root=temp_dir)

        assert preview["config_name"] == "editorconfig"
        assert preview["config_type"] == "editor_config"
        assert "root = true" in preview["source_content"]
        assert preview["target_content"] is None

    def test_preview_merge_with_existing_target(self, temp_dir: Path, sample_profile_dir: Path) -> None:
        target = temp_dir / ".editorconfig"
        target.write_text("root = false\nindent_size = 2\n", encoding="utf-8")

        orch = self._make_orchestrator(temp_dir, sample_profile_dir)
        namespace = sample_profile_dir.name

        preview = orch.preview_merge(namespace, "editorconfig", project_root=temp_dir)

        assert preview["source_content"] is not None
        assert preview["target_content"] is not None
        assert "indent_size = 2" in preview["target_content"]

    def test_apply_merge_writes_content(self, temp_dir: Path, sample_profile_dir: Path) -> None:
        orch = self._make_orchestrator(temp_dir, sample_profile_dir)
        namespace = sample_profile_dir.name
        target_path = str(temp_dir / ".editorconfig")
        merged = "root = true\nindent_size = 4\n"

        record = orch.apply_merge(namespace, "editorconfig", merged, target_path)

        assert record.status == MergeStatus.MERGED
        assert Path(target_path).read_text(encoding="utf-8") == merged
        assert record.backup_path is None  # No prior file to back up

    def test_apply_merge_creates_backup(self, temp_dir: Path, sample_profile_dir: Path) -> None:
        target_path = temp_dir / ".editorconfig"
        target_path.write_text("original content\n", encoding="utf-8")

        orch = self._make_orchestrator(temp_dir, sample_profile_dir)
        namespace = sample_profile_dir.name
        merged = "merged content\n"

        record = orch.apply_merge(namespace, "editorconfig", merged, str(target_path))

        assert record.status == MergeStatus.MERGED
        assert record.backup_path is not None
        assert Path(record.backup_path).exists()
        assert Path(record.backup_path).read_text(encoding="utf-8") == "original content\n"

    def test_get_merge_status_pending(self, temp_dir: Path, sample_profile_dir: Path) -> None:
        orch = self._make_orchestrator(temp_dir, sample_profile_dir)
        namespace = sample_profile_dir.name

        statuses = orch.get_merge_status(namespace, project_root=temp_dir)

        assert len(statuses) == 3
        assert all(s["status"] == "pending" for s in statuses)

    def test_get_merge_status_merged(self, temp_dir: Path, sample_profile_dir: Path) -> None:
        orch = self._make_orchestrator(temp_dir, sample_profile_dir)
        namespace = sample_profile_dir.name
        target_path = str(temp_dir / ".editorconfig")
        merged = "merged\n"

        orch.apply_merge(namespace, "editorconfig", merged, target_path)

        statuses = orch.get_merge_status(namespace, project_root=temp_dir)
        editor_status = next(s for s in statuses if s["config_name"] == "editorconfig")
        assert editor_status["status"] == "merged"

    def test_get_merge_status_changed(self, temp_dir: Path, sample_profile_dir: Path) -> None:
        orch = self._make_orchestrator(temp_dir, sample_profile_dir)
        namespace = sample_profile_dir.name
        target_path = temp_dir / ".editorconfig"

        orch.apply_merge(namespace, "editorconfig", "merged\n", str(target_path))
        target_path.write_text("user modified this\n", encoding="utf-8")

        statuses = orch.get_merge_status(namespace, project_root=temp_dir)
        editor_status = next(s for s in statuses if s["config_name"] == "editorconfig")
        assert editor_status["status"] == "changed"
