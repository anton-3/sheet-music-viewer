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

    def get_starred_pdfs(self) -> set[Path]:
        raw_value = self._settings.value("library/starred_pdfs", [])
        if isinstance(raw_value, str):
            candidates = [raw_value]
        elif isinstance(raw_value, list):
            candidates = [str(value) for value in raw_value]
        else:
            candidates = []

        starred: set[Path] = set()
        for candidate in candidates:
            path = Path(candidate).expanduser()
            if path.exists() and path.is_file() and path.suffix.lower() == ".pdf":
                starred.add(path.resolve())
        return starred

    def set_starred_pdfs(self, paths: set[Path]) -> None:
        serialized = sorted(str(path.expanduser().resolve()) for path in paths)
        self._settings.setValue("library/starred_pdfs", serialized)

    def is_pdf_starred(self, path: Path) -> bool:
        return path.expanduser().resolve() in self.get_starred_pdfs()

    def toggle_pdf_star(self, path: Path) -> bool:
        resolved = path.expanduser().resolve()
        starred = self.get_starred_pdfs()
        if resolved in starred:
            starred.remove(resolved)
            self.set_starred_pdfs(starred)
            return False

        starred.add(resolved)
        self.set_starred_pdfs(starred)
        return True
