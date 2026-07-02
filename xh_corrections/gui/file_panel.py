"""
FilPanel — panel for selecting and loading the account balances Excel file.

Emits:
    file_loaded(balances: dict, total: int)  — on successful load
    file_cleared()                            — when path is cleared
"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from xh_corrections.core.balances_loader import load_balances
from xh_corrections.gui.styles import (
    XH_RED, XH_GREEN, XH_MUTED, XH_BORDER,
    BUTTON_STYLE, INPUT_STYLE,
)


class FilePanel(QGroupBox):
    file_loaded = Signal(dict, int)   # balances, total_policies
    file_cleared = Signal()

    def __init__(self, parent=None):
        super().__init__("Qalıq faylı / Файл остатков (31.03.2026)", parent)
        self._balances: dict = {}
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)
        vbox.setSpacing(6)

        # Row: path field + Browse button
        row = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText(
            "Excel faylını seçin / Выберите Excel файл с остатками..."
        )
        self._path_edit.setReadOnly(True)
        self._path_edit.setStyleSheet(INPUT_STYLE)

        btn_browse = QPushButton("Seç / Обзор...")
        btn_browse.setStyleSheet(BUTTON_STYLE)
        btn_browse.setFixedWidth(130)
        btn_browse.clicked.connect(self._browse)

        row.addWidget(self._path_edit)
        row.addWidget(btn_browse)
        vbox.addLayout(row)

        # Status label
        self._status = QLabel("Fayl seçilməyib / Файл не выбран")
        self._status.setStyleSheet(f"color: {XH_MUTED}; font-size: 12px;")
        vbox.addWidget(self._status)

    # ------------------------------------------------------------------
    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Qalıq faylını seçin / Выберите файл остатков",
            "",
            "Excel files (*.xlsx *.xls);;All files (*)",
        )
        if not path:
            return
        self._load_file(path)

    def _load_file(self, path: str) -> None:
        try:
            balances, total = load_balances(path)
        except Exception as exc:
            self._path_edit.setText(path)
            self._status.setText(f"❌ Xəta / Ошибка: {exc}")
            self._status.setStyleSheet("color: #C8102E; font-size: 12px;")
            self.file_cleared.emit()
            return

        self._balances = balances
        self._path_edit.setText(path)
        self._status.setText(
            f"✓  Yükləndi / Загружено: {total:,} polis / полисов"
        )
        self._status.setStyleSheet(f"color: {XH_GREEN}; font-size: 12px;")
        self.file_loaded.emit(balances, total)

    # ------------------------------------------------------------------
    @property
    def balances(self) -> dict:
        return self._balances

    def is_loaded(self) -> bool:
        return bool(self._balances)
