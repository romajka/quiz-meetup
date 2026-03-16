from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from quiz_meetup.config import APP_NAME


@dataclass(slots=True)
class ApplicationPaths:
    app_data_dir: Path
    database_path: Path
    media_dir: Path


def _resolve_data_root() -> Path:
    if sys.platform.startswith("win"):
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / APP_NAME


def build_application_paths() -> ApplicationPaths:
    app_data_dir = _resolve_data_root()
    fallback_dir = Path.cwd() / ".quiz_meetup_data"
    media_dir = app_data_dir / "media"

    try:
        app_data_dir.mkdir(parents=True, exist_ok=True)
        media_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        app_data_dir = fallback_dir
        media_dir = app_data_dir / "media"
        app_data_dir.mkdir(parents=True, exist_ok=True)
        media_dir.mkdir(parents=True, exist_ok=True)

    return ApplicationPaths(
        app_data_dir=app_data_dir,
        database_path=app_data_dir / "quiz_meetup.db",
        media_dir=media_dir,
    )
