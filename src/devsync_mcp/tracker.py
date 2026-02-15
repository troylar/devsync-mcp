"""Merge tracking persistence."""

import json
import logging
from pathlib import Path
from typing import Optional

from devsync_mcp.models import BackupRecord, MergeRecord

logger = logging.getLogger(__name__)

DEFAULT_MERGES_PATH = Path.home() / ".devsync" / "merges.json"


class MergeTracker:
    """Persists merge records and backup references to ~/.devsync/merges.json."""

    def __init__(self, merges_path: Optional[Path] = None) -> None:
        self.merges_path = merges_path or DEFAULT_MERGES_PATH
        self.merges_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, list[dict[str, str]]]:
        if not self.merges_path.exists():
            return {"merges": [], "backups": []}
        with open(self.merges_path, "r", encoding="utf-8") as f:
            result: dict[str, list[dict[str, str]]] = json.load(f)
            return result

    def _save(self, data: dict) -> None:
        with open(self.merges_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_merge(self, record: MergeRecord) -> None:
        data = self._load()
        data["merges"].append(record.to_dict())
        self._save(data)

    def add_backup(self, record: BackupRecord) -> None:
        data = self._load()
        data["backups"].append(record.to_dict())
        self._save(data)

    def get_merges(self, profile_name: Optional[str] = None) -> list[MergeRecord]:
        data = self._load()
        records = [MergeRecord.from_dict(m) for m in data.get("merges", [])]
        if profile_name:
            records = [r for r in records if r.profile_name == profile_name]
        return records

    def get_backups(self, config_name: Optional[str] = None) -> list[BackupRecord]:
        data = self._load()
        records = [BackupRecord.from_dict(b) for b in data.get("backups", [])]
        if config_name:
            records = [r for r in records if r.config_name == config_name]
        return records

    def get_latest_merge(self, config_name: str, profile_name: str) -> Optional[MergeRecord]:
        merges = self.get_merges(profile_name)
        matching = [m for m in merges if m.config_name == config_name]
        if not matching:
            return None
        return max(matching, key=lambda m: m.merged_at)

    def get_status_summary(self, profile_name: str) -> dict[str, str]:
        """Get status of each config in a profile (config_name -> status)."""
        merges = self.get_merges(profile_name)
        status_map: dict[str, str] = {}
        for merge in sorted(merges, key=lambda m: m.merged_at):
            status_map[merge.config_name] = merge.status.value
        return status_map
