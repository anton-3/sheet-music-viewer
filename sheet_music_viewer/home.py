from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sheet_music_viewer.library import LibraryItem, list_library_items
from sheet_music_viewer.settings import AppSettings


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

        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self._go_back)

        self.change_root_button = QPushButton("Set Root")
        self.change_root_button.clicked.connect(self._choose_root_directory)

        header_layout = QHBoxLayout()
        header_layout.addWidget(self.back_button)
        header_layout.addWidget(self.change_root_button)
        header_layout.addWidget(self.path_label, stretch=1)

        self.list_widget = QListWidget()
        self.list_widget.itemActivated.connect(self._activate_item)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addLayout(header_layout)
        layout.addWidget(self.list_widget)
        self.setCentralWidget(container)

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
            QPushButton:disabled {
                color: #7d7d7d;
                background: #dcdcdc;
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
        self._choose_root_directory()

    def _choose_root_directory(self) -> None:
        while True:
            typed_path, accepted = QInputDialog.getText(
                self,
                "Set Library Root",
                "Enter the folder path containing your sheet music PDFs:",
                text="~/Documents/sheets",
            )
            if not accepted:
                return

            candidate = Path(typed_path).expanduser()
            if candidate.exists() and candidate.is_dir():
                self.settings.set_root_directory(candidate)
                self._set_root_directory(candidate)
                return

            QMessageBox.warning(self, "Invalid Folder", f"'{candidate}' is not a readable directory.")

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
