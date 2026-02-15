"""Tests for merge tracker persistence."""

from pathlib import Path

from devsync_mcp.models import BackupRecord, MergeRecord, MergeStatus
from devsync_mcp.tracker import MergeTracker


class TestMergeTracker:
    def test_add_and_get_merge(self, temp_dir: Path) -> None:
        tracker = MergeTracker(merges_path=temp_dir / "merges.json")

        record = MergeRecord(
            config_name="editorconfig",
            profile_name="acme-team",
            source_path="editor/.editorconfig",
            target_path="/home/user/.editorconfig",
            backup_path=None,
            source_checksum="abc123",
            target_checksum_before=None,
            target_checksum_after="def456",
            status=MergeStatus.MERGED,
        )
        tracker.add_merge(record)

        merges = tracker.get_merges()
        assert len(merges) == 1
        assert merges[0].config_name == "editorconfig"
        assert merges[0].status == MergeStatus.MERGED

    def test_filter_by_profile(self, temp_dir: Path) -> None:
        tracker = MergeTracker(merges_path=temp_dir / "merges.json")

        for profile in ["acme", "beta"]:
            tracker.add_merge(
                MergeRecord(
                    config_name="test",
                    profile_name=profile,
                    source_path="f",
                    target_path="t",
                    backup_path=None,
                    source_checksum="a",
                    target_checksum_before=None,
                    target_checksum_after="b",
                    status=MergeStatus.MERGED,
                )
            )

        assert len(tracker.get_merges("acme")) == 1
        assert len(tracker.get_merges("beta")) == 1
        assert len(tracker.get_merges()) == 2

    def test_add_and_get_backup(self, temp_dir: Path) -> None:
        tracker = MergeTracker(merges_path=temp_dir / "merges.json")

        record = BackupRecord(
            original_path="/home/user/.zshrc",
            backup_path="/home/user/.devsync/backups/zshrc_20260215.sh",
            config_name="zshrc",
            profile_name="acme",
            checksum="abc123",
        )
        tracker.add_backup(record)

        backups = tracker.get_backups()
        assert len(backups) == 1
        assert backups[0].config_name == "zshrc"

    def test_get_latest_merge(self, temp_dir: Path) -> None:
        tracker = MergeTracker(merges_path=temp_dir / "merges.json")

        for i in range(3):
            tracker.add_merge(
                MergeRecord(
                    config_name="test",
                    profile_name="acme",
                    source_path="f",
                    target_path="t",
                    backup_path=None,
                    source_checksum="a",
                    target_checksum_before=None,
                    target_checksum_after=f"checksum_{i}",
                    status=MergeStatus.MERGED,
                )
            )

        latest = tracker.get_latest_merge("test", "acme")
        assert latest is not None
        assert latest.target_checksum_after == "checksum_2"

    def test_status_summary(self, temp_dir: Path) -> None:
        tracker = MergeTracker(merges_path=temp_dir / "merges.json")

        tracker.add_merge(
            MergeRecord(
                config_name="zshrc",
                profile_name="acme",
                source_path="f",
                target_path="t",
                backup_path=None,
                source_checksum="a",
                target_checksum_before=None,
                target_checksum_after="b",
                status=MergeStatus.MERGED,
            )
        )

        summary = tracker.get_status_summary("acme")
        assert summary["zshrc"] == "merged"
