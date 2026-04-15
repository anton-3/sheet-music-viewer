from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MarkupStroke:
    page_index: int
    points: list[tuple[float, float]]
    color: str
    width: float


class MarkupStore:
    def __init__(self) -> None:
        self._pdf_path: Path | None = None
        self._strokes: list[MarkupStroke] = []
        self._undo_stack: list[tuple[str, MarkupStroke]] = []
        self._saved_snapshot: list[MarkupStroke] = []

    def load(self, pdf_path: Path) -> None:
        self.clear()
        self._pdf_path = pdf_path
        sidecar = self._sidecar_path()
        if sidecar is None or not sidecar.exists():
            return
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if not isinstance(data, dict) or data.get("version") != 1:
            return
        for entry in data.get("strokes", []):
            try:
                stroke = MarkupStroke(
                    page_index=int(entry["page"]),
                    points=[(float(p[0]), float(p[1])) for p in entry["points"]],
                    color=str(entry["color"]),
                    width=float(entry["width"]),
                )
                self._strokes.append(stroke)
            except (KeyError, TypeError, ValueError, IndexError):
                continue
        self._saved_snapshot = list(self._strokes)

    def save(self) -> bool:
        sidecar = self._sidecar_path()
        if sidecar is None:
            return False
        entries = []
        for stroke in self._strokes:
            entries.append({
                "page": stroke.page_index,
                "points": list(stroke.points),
                "color": stroke.color,
                "width": stroke.width,
            })
        data = {"version": 1, "strokes": entries}
        try:
            sidecar.write_text(json.dumps(data), encoding="utf-8")
        except OSError:
            return False
        self._saved_snapshot = list(self._strokes)
        return True

    def clear(self) -> None:
        self._pdf_path = None
        self._strokes.clear()
        self._undo_stack.clear()
        self._saved_snapshot.clear()

    def add_stroke(self, stroke: MarkupStroke) -> None:
        self._strokes.append(stroke)
        self._undo_stack.append(("draw", stroke))

    def remove_stroke(self, stroke: MarkupStroke) -> None:
        try:
            self._strokes.remove(stroke)
        except ValueError:
            return
        self._undo_stack.append(("erase", stroke))

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        action, stroke = self._undo_stack.pop()
        if action == "draw":
            try:
                self._strokes.remove(stroke)
            except ValueError:
                pass
        elif action == "erase":
            self._strokes.append(stroke)
        return True

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def strokes_for_page(self, page_index: int) -> list[MarkupStroke]:
        return [s for s in self._strokes if s.page_index == page_index]

    def all_strokes(self) -> list[MarkupStroke]:
        return list(self._strokes)

    @property
    def has_unsaved_changes(self) -> bool:
        return self._strokes != self._saved_snapshot

    def _sidecar_path(self) -> Path | None:
        if self._pdf_path is None:
            return None
        return self._pdf_path.parent / (self._pdf_path.name + ".markup.json")
