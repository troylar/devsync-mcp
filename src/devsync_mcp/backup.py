"""Backup management for merge operations."""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from devsync.core.checksum import calculate_file_checksum

from devsync_mcp.models import BackupRecord

logger = logging.getLogger(__name__)

DEFAULT_BACKUP_DIR = Path.home() / ".devsync" / "backups"


class BackupManager:
    """Creates and manages backups of config files before merging."""

    def __init__(self, backup_dir: Optional[Path] = None) -> None:
        self.backup_dir = backup_dir or DEFAULT_BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, file_path: Path, config_name: str, profile_name: str) -> Optional[BackupRecord]:
        """Create a backup of a file before merging.

        Returns None if the file doesn't exist (nothing to back up).
        """
        if not file_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{config_name}_{timestamp}{file_path.suffix}"
        backup_path = self.backup_dir / profile_name / backup_name
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(file_path, backup_path)

        checksum = calculate_file_checksum(str(backup_path))

        record = BackupRecord(
            original_path=str(file_path),
            backup_path=str(backup_path),
            config_name=config_name,
            profile_name=profile_name,
            checksum=checksum,
        )

        logger.info("Created backup: %s -> %s", file_path, backup_path)
        return record

    def restore_backup(self, backup_path: str, target_path: Optional[str] = None) -> Path:
        """Restore a file from backup.

        Args:
            backup_path: Path to the backup file
            target_path: Override target (uses original path from backup record if None)

        Returns:
            Path where the file was restored to
        """
        src = Path(backup_path)
        if not src.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")

        if target_path:
            dest = Path(target_path)
        else:
            raise ValueError("target_path is required when not using a BackupRecord")

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

        logger.info("Restored backup: %s -> %s", src, dest)
        return dest

    def list_backups(self, profile_name: Optional[str] = None) -> list[dict]:
        """List all backup files, optionally filtered by profile."""
        results: list[dict] = []

        search_dir = self.backup_dir / profile_name if profile_name else self.backup_dir

        if not search_dir.exists():
            return results

        for f in sorted(search_dir.rglob("*")):
            if f.is_file():
                rel_profile = f.parent.name if f.parent != self.backup_dir else "unknown"
                results.append(
                    {
                        "backup_path": str(f),
                        "profile_name": rel_profile,
                        "filename": f.name,
                        "size": f.stat().st_size,
                        "created_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                    }
                )

        return results
