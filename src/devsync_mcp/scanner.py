"""Environment scanner — detects existing config files."""

import logging
from pathlib import Path
from typing import Optional

from devsync.core.checksum import calculate_file_checksum

from devsync_mcp.config import CONFIG_PATTERNS, ConfigType, expand_target_path, is_platform_relevant
from devsync_mcp.models import DetectedConfig

logger = logging.getLogger(__name__)


class EnvironmentScanner:
    """Scans the user's environment for existing configuration files."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.project_root = project_root or Path.cwd()
        self.home = Path.home()

    def scan_all(self) -> list[DetectedConfig]:
        """Scan for all known config file types."""
        detected: list[DetectedConfig] = []

        for config_type, patterns in CONFIG_PATTERNS.items():
            if not is_platform_relevant(config_type):
                continue
            for pattern in patterns:
                found = self._check_pattern(pattern, config_type)
                if found:
                    detected.extend(found)

        return detected

    def scan_for_target(self, target: str) -> Optional[DetectedConfig]:
        """Check if a specific target path exists and return its info."""
        path = expand_target_path(target, self.project_root)
        if not path.exists():
            return DetectedConfig(
                path=str(path),
                config_type=ConfigType.CUSTOM,
                exists=False,
            )

        if path.is_dir():
            return self._scan_directory(path)

        return self._build_detected(path)

    def _check_pattern(self, pattern: str, config_type: ConfigType) -> list[DetectedConfig]:
        """Check a single pattern against the filesystem."""
        results: list[DetectedConfig] = []

        if pattern.endswith("/"):
            dir_path = self._resolve_pattern_path(pattern.rstrip("/"))
            if dir_path and dir_path.is_dir():
                for f in sorted(dir_path.iterdir()):
                    if f.is_file():
                        results.append(self._build_detected(f, config_type))
        else:
            file_path = self._resolve_pattern_path(pattern)
            if file_path and file_path.is_file():
                results.append(self._build_detected(file_path, config_type))

        return results

    def _resolve_pattern_path(self, pattern: str) -> Optional[Path]:
        """Resolve a pattern to an absolute path, checking both home and project."""
        candidates = [
            self.home / pattern,
            self.project_root / pattern,
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _scan_directory(self, dir_path: Path) -> DetectedConfig:
        """Scan a directory and return a summary."""
        total_size = sum(f.stat().st_size for f in dir_path.rglob("*") if f.is_file())
        from devsync_mcp.config import detect_config_type

        return DetectedConfig(
            path=str(dir_path),
            config_type=detect_config_type(dir_path.name),
            exists=True,
            size=total_size,
        )

    def _build_detected(self, path: Path, config_type: Optional[ConfigType] = None) -> DetectedConfig:
        """Build a DetectedConfig from a file path."""
        from devsync_mcp.config import detect_config_type

        try:
            checksum = calculate_file_checksum(str(path))
            size = path.stat().st_size
        except OSError:
            checksum = ""
            size = 0

        return DetectedConfig(
            path=str(path),
            config_type=config_type or detect_config_type(path.name),
            exists=True,
            size=size,
            checksum=checksum,
        )
