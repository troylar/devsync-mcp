"""Team profile management — wraps devsync's git/library operations."""

import logging
from pathlib import Path
from typing import Optional

import yaml
from devsync.core.git_operations import GitOperations

from devsync_mcp.config import ConfigType, detect_config_type
from devsync_mcp.models import ProfileConfig, TeamProfile

logger = logging.getLogger(__name__)

MANIFEST_NAMES = ["devsync-profile.yaml", "devsync-profile.yml", "templatekit.yaml", "templatekit.yml"]
DEFAULT_PROFILES_DIR = Path.home() / ".devsync" / "profiles"


class ProfileManager:
    """Manages team config profiles stored in ~/.devsync/profiles/."""

    def __init__(self, profiles_dir: Optional[Path] = None) -> None:
        self.profiles_dir = profiles_dir or DEFAULT_PROFILES_DIR
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def pull_profile(self, source: str, namespace: Optional[str] = None) -> TeamProfile:
        """Clone or pull a team profile repo.

        Args:
            source: Git URL or local path
            namespace: Override namespace (auto-derived if None)

        Returns:
            Parsed TeamProfile
        """
        if namespace is None:
            namespace = self._derive_namespace(source)

        dest = self.profiles_dir / namespace

        if dest.exists() and (dest / ".git").exists():
            self._pull_existing(dest)
        else:
            GitOperations.clone_repository(source, target_dir=dest, depth=1)

        profile = self._parse_manifest(dest)
        profile.source_url = source
        profile.namespace = namespace
        return profile

    def list_profiles(self) -> list[TeamProfile]:
        """List all pulled profiles."""
        profiles: list[TeamProfile] = []
        if not self.profiles_dir.exists():
            return profiles
        for child in sorted(self.profiles_dir.iterdir()):
            if child.is_dir():
                try:
                    profile = self._parse_manifest(child)
                    profile.namespace = child.name
                    profiles.append(profile)
                except Exception:
                    logger.warning("Failed to parse profile at %s", child)
        return profiles

    def get_profile(self, namespace: str) -> Optional[TeamProfile]:
        """Get a specific profile by namespace."""
        dest = self.profiles_dir / namespace
        if not dest.exists():
            return None
        try:
            profile = self._parse_manifest(dest)
            profile.namespace = namespace
            return profile
        except Exception:
            return None

    def get_config_content(self, namespace: str, config_file: str) -> Optional[str]:
        """Read the content of a config file from a profile.

        Args:
            namespace: Profile namespace
            config_file: Relative path to config file within the profile

        Returns:
            File content or None if not found
        """
        file_path = self.profiles_dir / namespace / config_file
        if not file_path.exists():
            return None
        if not file_path.resolve().is_relative_to(self.profiles_dir.resolve()):
            raise ValueError("Path traversal detected")
        return file_path.read_text(encoding="utf-8")

    def _derive_namespace(self, source: str) -> str:
        """Derive a filesystem-safe namespace from a source URL or path."""
        import re

        if source.startswith(("http://", "https://", "git@")):
            clean = re.sub(r"^(https?://|git@)", "", source)
            clean = re.sub(r"\.git$", "", clean)
            clean = re.sub(r":", "/", clean)
            parts = clean.strip("/").split("/")
            if len(parts) >= 2:
                return f"{parts[-2]}-{parts[-1]}".lower()
            return re.sub(r"[^a-z0-9-]", "-", parts[-1].lower())
        return Path(source).resolve().name.lower()

    def _pull_existing(self, repo_path: Path) -> None:
        """Pull latest changes for an existing repo."""
        import subprocess

        try:
            subprocess.run(
                ["git", "pull", "--ff-only"],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
            )
        except subprocess.CalledProcessError as e:
            logger.warning("Failed to pull updates: %s", e.stderr)

    def _parse_manifest(self, profile_dir: Path) -> TeamProfile:
        """Parse the profile manifest file."""
        manifest_path = None
        for name in MANIFEST_NAMES:
            candidate = profile_dir / name
            if candidate.exists():
                manifest_path = candidate
                break

        if manifest_path is None:
            return self._build_profile_from_directory(profile_dir)

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        configs = []
        for cfg_data in data.get("configs", []):
            config_type = (
                ConfigType(cfg_data.get("type", "custom"))
                if "type" in cfg_data
                else detect_config_type(cfg_data.get("target", cfg_data.get("file", "")))
            )
            configs.append(
                ProfileConfig(
                    name=cfg_data["name"],
                    file=cfg_data["file"],
                    target=cfg_data.get("target", cfg_data["file"]),
                    config_type=config_type,
                    description=cfg_data.get("description", ""),
                )
            )

        return TeamProfile(
            name=data.get("name", profile_dir.name),
            description=data.get("description", ""),
            version=data.get("version", "0.0.0"),
            configs=configs,
            source_url=data.get("source_url", ""),
        )

    def _build_profile_from_directory(self, profile_dir: Path) -> TeamProfile:
        """Build a profile by scanning directory contents (no manifest)."""
        configs: list[ProfileConfig] = []
        for f in sorted(profile_dir.rglob("*")):
            if f.is_file() and not f.name.startswith("."):
                rel = str(f.relative_to(profile_dir))
                config_type = detect_config_type(rel)
                configs.append(
                    ProfileConfig(
                        name=f.stem,
                        file=rel,
                        target=rel,
                        config_type=config_type,
                    )
                )

        return TeamProfile(
            name=profile_dir.name,
            description="Auto-discovered profile (no manifest)",
            version="0.0.0",
            configs=configs,
        )
