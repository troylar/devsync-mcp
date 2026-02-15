"""FastMCP server exposing all devsync-mcp tools."""

import logging
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

from devsync_mcp.backup import BackupManager
from devsync_mcp.merger import MergeOrchestrator
from devsync_mcp.profile import ProfileManager
from devsync_mcp.scanner import EnvironmentScanner
from devsync_mcp.tracker import MergeTracker

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "devsync-mcp",
    instructions="AI-merge of team dev configurations. Provides tools to pull team config profiles, "
    "preview merges (returning source + target for LLM-based intelligent merge), apply merged content, "
    "and manage backups.",
)

_profile_manager: Optional[ProfileManager] = None
_tracker: Optional[MergeTracker] = None
_backup_manager: Optional[BackupManager] = None
_orchestrator: Optional[MergeOrchestrator] = None


def _get_profile_manager() -> ProfileManager:
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = ProfileManager()
    return _profile_manager


def _get_tracker() -> MergeTracker:
    global _tracker
    if _tracker is None:
        _tracker = MergeTracker()
    return _tracker


def _get_backup_manager() -> BackupManager:
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager()
    return _backup_manager


def _get_orchestrator() -> MergeOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MergeOrchestrator(
            profile_manager=_get_profile_manager(),
            tracker=_get_tracker(),
            backup_manager=_get_backup_manager(),
        )
    return _orchestrator


# --- Implementation functions (testable without MCP) ---


def _pull_team_profile(git_url: str, namespace: Optional[str] = None) -> dict:
    pm = _get_profile_manager()
    profile = pm.pull_profile(git_url, namespace)
    return {
        "status": "ok",
        "profile": profile.to_dict(),
        "message": f"Pulled profile '{profile.name}' with {len(profile.configs)} config(s)",
    }


def _list_profile_configs(namespace: str) -> dict:
    pm = _get_profile_manager()
    profile = pm.get_profile(namespace)
    if not profile:
        return {"status": "error", "message": f"Profile not found: {namespace}"}
    return {
        "status": "ok",
        "profile_name": profile.name,
        "configs": [c.to_dict() for c in profile.configs],
    }


def _detect_current_configs(project_root: Optional[str] = None) -> dict:
    root = Path(project_root) if project_root else None
    scanner = EnvironmentScanner(project_root=root)
    detected = scanner.scan_all()
    return {
        "status": "ok",
        "detected": [d.to_dict() for d in detected],
        "total": len(detected),
    }


def _preview_merge(namespace: str, config_name: str, project_root: Optional[str] = None) -> dict:
    root = Path(project_root) if project_root else None
    orch = _get_orchestrator()
    try:
        preview = orch.preview_merge(namespace, config_name, project_root=root)
        return {"status": "ok", **preview}
    except (ValueError, FileNotFoundError) as e:
        return {"status": "error", "message": str(e)}


def _apply_merge(namespace: str, config_name: str, merged_content: str, target_path: str) -> dict:
    orch = _get_orchestrator()
    try:
        record = orch.apply_merge(namespace, config_name, merged_content, target_path)
        return {"status": "ok", "merge": record.to_dict()}
    except (ValueError, FileNotFoundError) as e:
        return {"status": "error", "message": str(e)}


def _sync_all(namespace: str, project_root: Optional[str] = None) -> dict:
    pm = _get_profile_manager()
    orch = _get_orchestrator()
    root = Path(project_root) if project_root else None

    profile = pm.get_profile(namespace)
    if not profile:
        return {"status": "error", "message": f"Profile not found: {namespace}"}

    if profile.source_url:
        try:
            pm.pull_profile(profile.source_url, namespace)
        except Exception as e:
            logger.warning("Failed to pull latest: %s", e)

    statuses = orch.get_merge_status(namespace, project_root=root)
    pending = [s for s in statuses if s["status"] == "pending"]
    changed = [s for s in statuses if s["status"] == "changed"]

    return {
        "status": "ok",
        "profile_name": profile.name,
        "items": statuses,
        "summary": {
            "total": len(statuses),
            "pending": len(pending),
            "merged": len(statuses) - len(pending) - len(changed),
            "changed": len(changed),
        },
    }


def _list_backups(profile_name: Optional[str] = None) -> dict:
    bm = _get_backup_manager()
    backups = bm.list_backups(profile_name)
    return {
        "status": "ok",
        "backups": backups,
        "total": len(backups),
    }


def _restore_backup(backup_path: str, target_path: str) -> dict:
    bm = _get_backup_manager()
    try:
        restored = bm.restore_backup(backup_path, target_path)
        return {"status": "ok", "restored_to": str(restored)}
    except (FileNotFoundError, ValueError) as e:
        return {"status": "error", "message": str(e)}


def _get_merge_status(namespace: str, project_root: Optional[str] = None) -> dict:
    orch = _get_orchestrator()
    root = Path(project_root) if project_root else None
    try:
        statuses = orch.get_merge_status(namespace, project_root=root)
        return {"status": "ok", "configs": statuses}
    except ValueError as e:
        return {"status": "error", "message": str(e)}


# --- MCP Tool Registration ---


@mcp.tool()
def pull_team_profile(git_url: str, namespace: Optional[str] = None) -> dict:
    """Clone or pull a team config profile repository into the local devsync library.

    Args:
        git_url: Git repository URL or local path containing team configs
        namespace: Override namespace (auto-derived from URL if not provided)

    Returns:
        Profile info with name, description, version, and list of configs
    """
    return _pull_team_profile(git_url, namespace)


@mcp.tool()
def list_profile_configs(namespace: str) -> dict:
    """List all config files in a pulled team profile.

    Args:
        namespace: Profile namespace (as returned by pull_team_profile)

    Returns:
        List of configs with name, type, target path, and description
    """
    return _list_profile_configs(namespace)


@mcp.tool()
def detect_current_configs(project_root: Optional[str] = None) -> dict:
    """Scan the user's environment for existing configuration files.

    Detects shell profiles, git configs, editor configs, AI rules, and more.

    Args:
        project_root: Project root directory (defaults to cwd)

    Returns:
        List of detected config files with paths, types, and checksums
    """
    return _detect_current_configs(project_root)


@mcp.tool()
def preview_merge(namespace: str, config_name: str, project_root: Optional[str] = None) -> dict:
    """Return source (team) and target (user) content for the LLM to intelligently merge.

    The MCP server does NOT perform the merge. It returns both contents so the host
    IDE's LLM can understand the semantics and produce an intelligent merge that
    preserves personal customizations while incorporating team standards.

    Args:
        namespace: Profile namespace
        config_name: Name of the config to merge (from list_profile_configs)
        project_root: Project root for project-relative targets

    Returns:
        Dict with source_content, target_content (None if no existing file),
        target_path, config_type, and description
    """
    return _preview_merge(namespace, config_name, project_root)


@mcp.tool()
def apply_merge(namespace: str, config_name: str, merged_content: str, target_path: str) -> dict:
    """Write LLM-merged content to the target path, creating a backup of the original.

    Call this AFTER the LLM has produced the merged content from preview_merge output.

    Args:
        namespace: Profile namespace
        config_name: Config name that was merged
        merged_content: The LLM's merged output to write
        target_path: File path to write the merged content to

    Returns:
        Merge record with backup path, checksums, and status
    """
    return _apply_merge(namespace, config_name, merged_content, target_path)


@mcp.tool()
def sync_all(namespace: str, project_root: Optional[str] = None) -> dict:
    """Pull latest profile, detect changes, and present a merge plan.

    This is a convenience tool that combines pull + status check into one call.
    Returns a plan showing which configs need merging.

    Args:
        namespace: Profile namespace
        project_root: Project root for project-relative targets

    Returns:
        Merge plan with status of each config (pending/merged/changed)
    """
    return _sync_all(namespace, project_root)


@mcp.tool()
def list_backups(profile_name: Optional[str] = None) -> dict:
    """List backup files from previous merge operations.

    Args:
        profile_name: Filter backups by profile (all if not specified)

    Returns:
        List of backup files with paths, sizes, and timestamps
    """
    return _list_backups(profile_name)


@mcp.tool()
def restore_backup(backup_path: str, target_path: str) -> dict:
    """Restore a config file from a previous backup.

    Args:
        backup_path: Path to the backup file (from list_backups)
        target_path: Where to restore the file

    Returns:
        Confirmation with restored path
    """
    return _restore_backup(backup_path, target_path)


@mcp.tool()
def get_merge_status(namespace: str, project_root: Optional[str] = None) -> dict:
    """Show the current merge status for all configs in a profile.

    For each config, reports whether it is:
    - pending: never been merged
    - merged: last merge matches current file
    - changed: file has been modified since last merge

    Args:
        namespace: Profile namespace
        project_root: Project root for project-relative targets

    Returns:
        List of config statuses
    """
    return _get_merge_status(namespace, project_root)


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
