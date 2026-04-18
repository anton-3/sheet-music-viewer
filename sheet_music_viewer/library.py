from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz


def pdf_page_count(path: Path) -> int | None:
    try:
        doc = fitz.open(path)
    except (OSError, RuntimeError, ValueError):
        return None
    try:
        return doc.page_count
    finally:
        doc.close()


@dataclass(frozen=True)
class LibraryItem:
    path: Path
    is_directory: bool
    page_count: int | None = None

    @property
    def display_name(self) -> str:
        return self.path.name or str(self.path)


def list_library_items(directory: Path) -> list[LibraryItem]:
    items: list[LibraryItem] = []
    for path in sorted(directory.iterdir(), key=lambda entry: (not entry.is_dir(), entry.name.lower())):
        if path.is_dir() and not path.name.startswith("."):
            items.append(LibraryItem(path=path, is_directory=True))
            continue
        if path.is_file() and path.suffix.lower() == ".pdf":
            items.append(LibraryItem(path=path, is_directory=False, page_count=pdf_page_count(path)))
    return items
