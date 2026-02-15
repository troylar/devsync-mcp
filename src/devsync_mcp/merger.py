"""Merge orchestration — preview and apply logic."""

import logging
from pathlib import Path
from typing import Optional

from devsync.core.checksum import calculate_checksum, calculate_file_checksum

from devsync_mcp.backup import BackupManager
from devsync_mcp.config import expand_target_path
from devsync_mcp.models import MergeRecord, MergeStatus, ProfileConfig
from devsync_mcp.profile import ProfileManager
from devsync_mcp.tracker import MergeTracker

logger = logging.getLogger(__name__)


class MergeOrchestrator:
    """Orchestrates preview and apply merge operations.

    The orchestrator does NOT call an LLM. It provides source and target content
    to the host IDE's LLM via preview_merge, then accepts the merged result via
    apply_merge.
    """

    def __init__(
        self,
        profile_manager: Optional[ProfileManager] = None,
        tracker: Optional[MergeTracker] = None,
        backup_manager: Optional[BackupManager] = None,
    ) -> None:
        self.profile_manager = profile_manager or ProfileManager()
        self.tracker = tracker or MergeTracker()
        self.backup_manager = backup_manager or BackupManager()

    def preview_merge(
        self,
        namespace: str,
        config_name: str,
        project_root: Optional[Path] = None,
    ) -> dict:
        """Return source + target content for the LLM to merge.

        Returns a dict with:
            - config_name: str
            - config_type: str
            - source_content: str (team profile content)
            - target_content: str | None (existing user content, None if no file)
            - target_path: str (where the merged result will be written)
            - description: str
        """
        profile = self.profile_manager.get_profile(namespace)
        if not profile:
            raise ValueError(f"Profile not found: {namespace}")

        config = self._find_config(profile.configs, config_name)
        if not config:
            raise ValueError(f"Config not found: {config_name} in profile {namespace}")

        source_content = self.profile_manager.get_config_content(namespace, config.file)
        if source_content is None:
            raise FileNotFoundError(f"Source file not found: {config.file} in profile {namespace}")

        target_path = expand_target_path(config.target, project_root)
        target_content: Optional[str] = None
        if target_path.exists() and target_path.is_file():
            target_content = target_path.read_text(encoding="utf-8")

        return {
            "config_name": config.name,
            "config_type": config.config_type.value,
            "source_content": source_content,
            "target_content": target_content,
            "target_path": str(target_path),
            "description": config.description,
        }

    def apply_merge(
        self,
        namespace: str,
        config_name: str,
        merged_content: str,
        target_path: str,
    ) -> MergeRecord:
        """Write the LLM-merged content to the target path with backup.

        Args:
            namespace: Profile namespace
            config_name: Config name within the profile
            merged_content: The LLM's merged output
            target_path: Where to write the result

        Returns:
            MergeRecord tracking the operation
        """
        profile = self.profile_manager.get_profile(namespace)
        if not profile:
            raise ValueError(f"Profile not found: {namespace}")

        config = self._find_config(profile.configs, config_name)
        if not config:
            raise ValueError(f"Config not found: {config_name}")

        dest = Path(target_path)

        # Backup existing file
        backup_record = self.backup_manager.create_backup(dest, config_name, namespace)
        if backup_record:
            self.tracker.add_backup(backup_record)

        # Calculate checksums
        source_content = self.profile_manager.get_config_content(namespace, config.file) or ""
        source_checksum = calculate_checksum(source_content)
        target_checksum_before = calculate_file_checksum(str(dest)) if dest.exists() else None

        # Write merged content
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(merged_content, encoding="utf-8")

        target_checksum_after = calculate_file_checksum(str(dest))

        record = MergeRecord(
            config_name=config_name,
            profile_name=namespace,
            source_path=config.file,
            target_path=str(dest),
            backup_path=backup_record.backup_path if backup_record else None,
            source_checksum=source_checksum,
            target_checksum_before=target_checksum_before,
            target_checksum_after=target_checksum_after,
            status=MergeStatus.MERGED,
        )

        self.tracker.add_merge(record)
        logger.info("Applied merge: %s -> %s", config_name, dest)
        return record

    def get_merge_status(self, namespace: str, project_root: Optional[Path] = None) -> list[dict]:
        """Get merge status for all configs in a profile.

        For each config, reports:
            - merged: last merge matches current target
            - changed: target has been modified since last merge
            - pending: never been merged
        """
        profile = self.profile_manager.get_profile(namespace)
        if not profile:
            raise ValueError(f"Profile not found: {namespace}")

        statuses: list[dict] = []
        for config in profile.configs:
            target_path = expand_target_path(config.target, project_root)
            latest = self.tracker.get_latest_merge(config.name, namespace)

            if latest is None:
                status = "pending"
            elif not target_path.exists():
                status = "pending"
            else:
                current_checksum = calculate_file_checksum(str(target_path))
                if current_checksum == latest.target_checksum_after:
                    status = "merged"
                else:
                    status = "changed"

            statuses.append(
                {
                    "config_name": config.name,
                    "config_type": config.config_type.value,
                    "target_path": str(target_path),
                    "status": status,
                    "description": config.description,
                }
            )

        return statuses

    def _find_config(self, configs: list[ProfileConfig], name: str) -> Optional[ProfileConfig]:
        for c in configs:
            if c.name == name:
                return c
        return None
