"""Data models for devsync-mcp."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from devsync_mcp.config import ConfigType


class MergeStatus(str, Enum):
    """Status of a merge operation."""

    PENDING = "pending"
    MERGED = "merged"
    SKIPPED = "skipped"
    FAILED = "failed"
    CHANGED = "changed"


@dataclass
class ProfileConfig:
    """A single config file within a team profile."""

    name: str
    file: str
    target: str
    config_type: ConfigType
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "file": self.file,
            "target": self.target,
            "type": self.config_type.value,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProfileConfig":
        return cls(
            name=data["name"],
            file=data["file"],
            target=data["target"],
            config_type=ConfigType(data.get("type", "custom")),
            description=data.get("description", ""),
        )


@dataclass
class TeamProfile:
    """A team profile containing multiple config files."""

    name: str
    description: str
    version: str
    configs: list[ProfileConfig] = field(default_factory=list)
    source_url: str = ""
    namespace: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "configs": [c.to_dict() for c in self.configs],
            "source_url": self.source_url,
            "namespace": self.namespace,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TeamProfile":
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "0.0.0"),
            configs=[ProfileConfig.from_dict(c) for c in data.get("configs", [])],
            source_url=data.get("source_url", ""),
            namespace=data.get("namespace", ""),
        )


@dataclass
class MergeRecord:
    """Record of a single merge operation."""

    config_name: str
    profile_name: str
    source_path: str
    target_path: str
    backup_path: Optional[str]
    source_checksum: str
    target_checksum_before: Optional[str]
    target_checksum_after: str
    status: MergeStatus
    merged_at: datetime = field(default_factory=datetime.now)
    error_message: str = ""

    def to_dict(self) -> dict:
        return {
            "config_name": self.config_name,
            "profile_name": self.profile_name,
            "source_path": self.source_path,
            "target_path": self.target_path,
            "backup_path": self.backup_path,
            "source_checksum": self.source_checksum,
            "target_checksum_before": self.target_checksum_before,
            "target_checksum_after": self.target_checksum_after,
            "status": self.status.value,
            "merged_at": self.merged_at.isoformat(),
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MergeRecord":
        return cls(
            config_name=data["config_name"],
            profile_name=data["profile_name"],
            source_path=data["source_path"],
            target_path=data["target_path"],
            backup_path=data.get("backup_path"),
            source_checksum=data["source_checksum"],
            target_checksum_before=data.get("target_checksum_before"),
            target_checksum_after=data["target_checksum_after"],
            status=MergeStatus(data["status"]),
            merged_at=datetime.fromisoformat(data["merged_at"]),
            error_message=data.get("error_message", ""),
        )


@dataclass
class BackupRecord:
    """Record of a backup file."""

    original_path: str
    backup_path: str
    config_name: str
    profile_name: str
    checksum: str
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "original_path": self.original_path,
            "backup_path": self.backup_path,
            "config_name": self.config_name,
            "profile_name": self.profile_name,
            "checksum": self.checksum,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BackupRecord":
        return cls(
            original_path=data["original_path"],
            backup_path=data["backup_path"],
            config_name=data["config_name"],
            profile_name=data["profile_name"],
            checksum=data["checksum"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class DetectedConfig:
    """A config file detected in the user's environment."""

    path: str
    config_type: ConfigType
    exists: bool
    size: int = 0
    checksum: str = ""

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "type": self.config_type.value,
            "exists": self.exists,
            "size": self.size,
            "checksum": self.checksum,
        }


@dataclass
class MergePlan:
    """Plan for syncing all configs from a profile."""

    profile_name: str
    items: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "profile_name": self.profile_name,
            "items": self.items,
            "total": len(self.items),
            "pending": sum(1 for i in self.items if i.get("status") == "pending"),
            "merged": sum(1 for i in self.items if i.get("status") == "merged"),
            "changed": sum(1 for i in self.items if i.get("status") == "changed"),
        }
