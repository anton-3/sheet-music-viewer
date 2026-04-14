from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LibraryItem:
    path: Path
    is_directory: bool

    @property
    def display_name(self) -> str:
        return self.path.name or str(self.path)


def list_library_items(directory: Path) -> list[LibraryItem]:
    items: list[LibraryItem] = []
    for path in sorted(directory.iterdir(), key=lambda entry: (not entry.is_dir(), entry.name.lower())):
        if path.is_dir():
            items.append(LibraryItem(path=path, is_directory=True))
            continue
        if path.is_file() and path.suffix.lower() == ".pdf":
            items.append(LibraryItem(path=path, is_directory=False))
    return items
