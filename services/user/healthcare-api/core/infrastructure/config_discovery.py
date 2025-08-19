"""Config Discovery Utilities

Discovers operational YAML configuration files using a small index file plus
controlled directory scanning. Avoids loading developer tooling YAML at repo root.

Precedence for locating a config file (e.g., rate_limits.yml):
1. Explicit environment variable specific to that loader (e.g., RL_YAML_PATH)
2. Config index (config/config_index.yml) if present and contains file name
3. Discovery roots (CONFIG_DISCOVERY_ROOT or default 'config') searched recursively
4. Fallback default data embedded in code

Environment variables:
- CONFIG_INDEX_PATH: optional explicit path to index (default: config/config_index.yml)
- CONFIG_DISCOVERY_ROOT: single root to search (default: config)

The index file contains relative paths under its own directory.
"""

from __future__ import annotations

import logging
from pathlib import Path

try:
    import yaml  # type: ignore

    _YAML_AVAILABLE = True
except Exception:  # pragma: no cover
    _YAML_AVAILABLE = False

logger = logging.getLogger(__name__)


def load_config_index(index_path: str | None = None) -> list[str]:
    if not _YAML_AVAILABLE:
        return []
    path = Path(index_path or "config/config_index.yml")
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        files = data.get("files", [])
        if not isinstance(files, list):  # pragma: no cover
            return []
        # Normalize
        return [str(Path(path.parent, f)) for f in files]
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to parse config index %s: %s", path, exc)
        return []


def find_config_file(
    filename: str, *, index_path: str | None = None, discovery_root: str = "config"
) -> str | None:
    # 1. Index lookup
    for p in load_config_index(index_path):
        if Path(p).name == filename and Path(p).exists():
            return p
    # 2. Discovery root scan
    root = Path(discovery_root)
    if root.exists():
        for match in root.rglob(filename):
            return str(match)
    return None


__all__ = ["find_config_file", "load_config_index"]
