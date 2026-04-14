from __future__ import annotations

from pathlib import Path

import fitz
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QImage


class PdfDocument:
    def __init__(self, pdf_path: Path) -> None:
        self.path = pdf_path
        self._document = fitz.open(pdf_path)
        self._cache: dict[tuple[int, int, int], QImage] = {}

    @property
    def page_count(self) -> int:
        return self._document.page_count

    def page_size(self, page_index: int) -> tuple[float, float]:
        page = self._document.load_page(page_index)
        rect = page.rect
        return rect.width, rect.height

    def render_page(self, page_index: int, target_size: QSize) -> QImage:
        width = max(1, target_size.width())
        height = max(1, target_size.height())
        cache_key = (page_index, width, height)
        if cache_key in self._cache:
            return self._cache[cache_key]

        page = self._document.load_page(page_index)
        rect = page.rect
        scale = min(width / rect.width, height / rect.height)
        scale = max(scale, 0.2)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)

        image_format = QImage.Format.Format_RGB888
        image = QImage(
            pixmap.samples,
            pixmap.width,
            pixmap.height,
            pixmap.stride,
            image_format,
        ).copy()
        self._cache[cache_key] = image
        return image

    def close(self) -> None:
        self._document.close()
        self._cache.clear()
