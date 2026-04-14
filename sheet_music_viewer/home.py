from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScroller,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sheet_music_viewer.library import LibraryItem, list_library_items
from sheet_music_viewer.settings import AppSettings


TAP_DRAG_THRESHOLD = 18
BACK_SWIPE_DISTANCE = 90


class LibraryListWidget(QListWidget):
    item_tapped = pyqtSignal(QListWidgetItem)
    back_swiped = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._press_pos: QPoint | None = None
        self._dragging = False

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position().toPoint()
            self._dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._press_pos is not None:
            distance = (event.position().toPoint() - self._press_pos).manhattanLength()
            if distance > TAP_DRAG_THRESHOLD:
                self._dragging = True
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._press_pos is not None:
            delta = event.position().toPoint() - self._press_pos
            distance = delta.manhattanLength()
            should_activate = not self._dragging and distance <= TAP_DRAG_THRESHOLD
            should_go_back = (
                delta.x() >= BACK_SWIPE_DISTANCE
                and abs(delta.x()) > abs(delta.y())
            )
            item = self.itemAt(event.position().toPoint()) if should_activate else None
            self._press_pos = None
            self._dragging = False
            super().mouseReleaseEvent(event)
            if should_go_back:
                self.back_swiped.emit()
                return
            if item is not None:
                self.item_tapped.emit(item)
            return
        self._press_pos = None
        self._dragging = False
        super().mouseReleaseEvent(event)


class SettingsDialog(QDialog):
    def __init__(self, current_root: Path | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._selected_root: Path | None = current_root

        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(520)

        self.root_value_label = QLabel(self._format_root(current_root))
        self.root_value_label.setWordWrap(True)

        change_root_button = QPushButton("Change Root Folder")
        change_root_button.clicked.connect(self._choose_root_directory)

        root_row = QHBoxLayout()
        root_row.setSpacing(12)
        root_row.addWidget(self.root_value_label, stretch=1)
        root_row.addWidget(change_root_button, stretch=0)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=self)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        layout.addLayout(root_row)
        layout.addStretch(1)
        layout.addWidget(buttons)

    def selected_root_directory(self) -> Path | None:
        return self._selected_root

    def _choose_root_directory(self) -> None:
        default_text = str(self._selected_root) if self._selected_root else "~/Documents"
        while True:
            typed_path, accepted = QInputDialog.getText(
                self,
                "Set Library Root",
                "Enter the folder path containing your sheet music PDFs:",
                text=default_text,
            )
            if not accepted:
                return

            candidate = Path(typed_path).expanduser()
            if candidate.exists() and candidate.is_dir():
                self._selected_root = candidate.resolve()
                self.root_value_label.setText(self._format_root(self._selected_root))
                return

            QMessageBox.warning(self, "Invalid Folder", f"'{candidate}' is not a readable directory.")

    def _format_root(self, path: Path | None) -> str:
        return str(path) if path else "Not configured"


class HomeWindow(QMainWindow):
    pdf_requested = pyqtSignal(object)

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.settings = settings
        self._root_directory: Path | None = None
        self._current_directory: Path | None = None
        self._history: list[Path] = []

        self.setWindowTitle("Sheet Music Viewer")
        self.resize(1000, 700)
        self._build_ui()
        self._apply_styles()
        self._ensure_root_directory()

    def show_home(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _build_ui(self) -> None:
        self.path_label = QLabel("No library selected")
        self.path_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.path_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self._go_back)

        self.settings_button = QPushButton("\u2699")
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.setToolTip("Settings")
        self.settings_button.clicked.connect(self._open_settings_dialog)

        header_layout = QHBoxLayout()
        header_layout.addWidget(self.back_button)
        header_layout.addWidget(self.path_label, stretch=1)
        header_layout.addWidget(self.settings_button)

        self.list_widget = LibraryListWidget()
        self._configure_library_list()
        self.list_widget.itemActivated.connect(self._activate_item)
        self.list_widget.item_tapped.connect(self._activate_item)
        self.list_widget.back_swiped.connect(self._go_back)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addLayout(header_layout)
        layout.addWidget(self.list_widget)
        self.setCentralWidget(container)

    def _configure_library_list(self) -> None:
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.list_widget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list_widget.setAutoScroll(False)
        self.list_widget.setUniformItemSizes(False)
        self.list_widget.setSpacing(2)

        QScroller.grabGesture(
            self.list_widget.viewport(),
            QScroller.ScrollerGestureType.LeftMouseButtonGesture,
        )
        QScroller.grabGesture(
            self.list_widget.viewport(),
            QScroller.ScrollerGestureType.TouchGesture,
        )

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #e8e8e8;
                color: #1c1c1c;
                font-size: 16px;
            }
            QPushButton {
                background: #d3d3d3;
                border: 1px solid #9a9a9a;
                padding: 10px 16px;
                min-width: 100px;
            }
            QPushButton#settingsButton {
                font-size: 22px;
                min-width: 52px;
                max-width: 52px;
                padding: 8px;
            }
            QPushButton:disabled {
                color: #7d7d7d;
                background: #dcdcdc;
            }
            QDialog {
                background: #efefef;
                color: #1c1c1c;
            }
            QLabel#settingsHintLabel {
                color: #666666;
            }
            QListWidget {
                background: #f4f4f4;
                border: 1px solid #b8b8b8;
                outline: none;
            }
            QListWidget::item {
                padding: 14px 10px;
                border-bottom: 1px solid #d6d6d6;
            }
            QListWidget::item:selected {
                background: #cfcfcf;
                color: #111111;
            }
            """
        )

    def _ensure_root_directory(self) -> None:
        stored_root = self.settings.get_root_directory()
        if stored_root:
            self._set_root_directory(stored_root)
            return
        if root_directory := self._prompt_for_root_directory():
            self.settings.set_root_directory(root_directory)
            self._set_root_directory(root_directory)

    def _prompt_for_root_directory(self, initial_path: Path | None = None) -> Path | None:
        default_text = str(initial_path) if initial_path else "~/Documents"
        while True:
            typed_path, accepted = QInputDialog.getText(
                self,
                "Set Library Root",
                "Enter the folder path containing your sheet music PDFs:",
                text=default_text,
            )
            if not accepted:
                return None

            candidate = Path(typed_path).expanduser()
            if candidate.exists() and candidate.is_dir():
                return candidate.resolve()

            QMessageBox.warning(self, "Invalid Folder", f"'{candidate}' is not a readable directory.")

    def _open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self._root_directory, self)
        if dialog.exec() != QDialog.DialogCode.Accepted and dialog.selected_root_directory() == self._root_directory:
            return

        new_root = dialog.selected_root_directory()
        if new_root is None or new_root == self._root_directory:
            return

        self.settings.set_root_directory(new_root)
        self._set_root_directory(new_root)

    def _set_root_directory(self, root_directory: Path) -> None:
        self._root_directory = root_directory.resolve()
        self._history.clear()
        self._navigate_to(self._root_directory)

    def _navigate_to(self, directory: Path) -> None:
        self._current_directory = directory
        self.path_label.setText(str(directory))
        self.back_button.setEnabled(bool(self._root_directory and directory != self._root_directory))
        self._reload_list()

    def _reload_list(self) -> None:
        assert self._current_directory is not None
        self.list_widget.clear()

        try:
            items = list_library_items(self._current_directory)
        except OSError as exc:
            QMessageBox.warning(self, "Folder Error", f"Could not read '{self._current_directory}': {exc}")
            items = []

        if not items:
            empty = QListWidgetItem("This folder has no PDFs or subfolders.")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_widget.addItem(empty)
            return

        for item in items:
            label = f"[DIR] {item.display_name}" if item.is_directory else item.display_name
            widget_item = QListWidgetItem(label)
            widget_item.setData(Qt.ItemDataRole.UserRole, item)
            self.list_widget.addItem(widget_item)

    def _activate_item(self, widget_item: QListWidgetItem) -> None:
        item = widget_item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(item, LibraryItem):
            return
        if item.is_directory:
            assert self._current_directory is not None
            self._history.append(self._current_directory)
            self._navigate_to(item.path)
            return
        self.pdf_requested.emit(item.path)

    def _go_back(self) -> None:
        if not self._history:
            return
        previous = self._history.pop()
        self._navigate_to(previous)
