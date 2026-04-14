from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSettings


class AppSettings:
    def __init__(self) -> None:
        self._settings = QSettings("sheet-music-viewer", "sheet-music-viewer")

    def get_root_directory(self) -> Path | None:
        raw_value = self._settings.value("library/root_directory", None)
        if not raw_value:
            return None

        path = Path(str(raw_value)).expanduser()
        return path if path.exists() and path.is_dir() else None

    def set_root_directory(self, path: Path) -> None:
        resolved = str(path.expanduser().resolve())
        self._settings.setValue("library/root_directory", resolved)
