"""
Main application window — Xalq Həyat Korrektəedici Müxabirləşmələr.
"""
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QPushButton, QScrollArea,
    QSizePolicy, QMessageBox, QFileDialog, QStatusBar,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPalette

from gui.styles import MAIN_STYLE, XH_RED, XH_WHITE, XH_MUTED, XH_BG, XH_DARK
from gui.connection_panel import ConnectionPanel
from gui.calc_panel import CalcPanel
from gui.results_panel import ResultsPanel


class HeaderBar(QWidget):
    """Fixed red header bar with logo text and version."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(54)
        self.setStyleSheet(f"background-color: {XH_RED};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)

        logo_lbl = QLabel("⟨Z⟩")
        logo_lbl.setFont(QFont("Segoe UI", 16, QFont.Bold))
        logo_lbl.setStyleSheet(f"color: {XH_WHITE}; background: transparent;")
        layout.addWidget(logo_lbl)

        layout.addSpacing(10)

        title_lbl = QLabel("Xalq Həyat — Korrektəedici Müxabirləşmələr")
        title_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title_lbl.setStyleSheet(f"color: {XH_WHITE}; background: transparent;")
        layout.addWidget(title_lbl)

        layout.addStretch()

        ver_lbl = QLabel("v1.0")
        ver_lbl.setFont(QFont("Segoe UI", 9))
        ver_lbl.setStyleSheet(f"color: rgba(255,255,255,180); background: transparent;")
        layout.addWidget(ver_lbl)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Xalq Həyat — Korrektəedici Müxabirləşmələr")
        self.setFixedWidth(860)
        self.setMinimumHeight(720)
        self.setStyleSheet(MAIN_STYLE)

        self._corrections: list[dict] = []
        self._hitam: list[str] = []
        self._total_policies: int = 0
        self._report_date: str = ""
        self._last_export_path: str = ""

        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------ #
    #  UI construction
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        root.addWidget(HeaderBar())

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        content = QWidget()
        content.setStyleSheet(f"background-color: {XH_BG};")
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Section 1 — Connection
        self.conn_panel = ConnectionPanel()
        layout.addWidget(self.conn_panel)

        # Section 2 — Calculation
        self.calc_panel = CalcPanel()
        layout.addWidget(self.calc_panel)

        # Section 3 — Results
        self.results_panel = ResultsPanel()
        self.results_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.results_panel, stretch=1)

        # Bottom export button row
        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 4, 0, 0)

        self.btn_export = QPushButton("Excel-ə ixrac / Выгрузить в Excel")
        self.btn_export.setObjectName("btn_primary")
        self.btn_export.setEnabled(False)
        self.btn_export.setMinimumHeight(38)
        self.btn_export.setMinimumWidth(240)
        self.btn_export.clicked.connect(self._on_export)
        bottom.addWidget(self.btn_export)
        bottom.addStretch()

        layout.addLayout(bottom)

        root.addWidget(scroll)

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Hazır / Готово")

    # ------------------------------------------------------------------ #
    #  Signal wiring
    # ------------------------------------------------------------------ #

    def _connect_signals(self):
        self.conn_panel.connected.connect(self._on_connected)
        self.conn_panel.disconnected.connect(self._on_disconnected)

        self.calc_panel.calculation_started.connect(self._on_calc_started)
        self.calc_panel.calculation_done.connect(self._on_calc_done)
        self.calc_panel.calculation_error.connect(self._on_calc_error)

    # ------------------------------------------------------------------ #
    #  Slots
    # ------------------------------------------------------------------ #

    def _on_connected(self, conn):
        self.calc_panel.set_connection(conn)
        self.status.showMessage("Bağlantı uğurludur / Подключение установлено")

    def _on_disconnected(self):
        self.calc_panel.clear_connection()
        self.btn_export.setEnabled(False)
        self.status.showMessage("Bağlantı yoxdur / Нет подключения")

    def _on_calc_started(self):
        self.btn_export.setEnabled(False)
        self.results_panel.clear()
        self.status.showMessage("Yüklənir... / Загрузка данных...")

    def _on_calc_done(self, corrections: list, hitam: list, total_policies: int, report_date: str):
        self._corrections   = corrections
        self._hitam         = hitam
        self._total_policies = total_policies
        self._report_date   = report_date

        self.results_panel.set_results(corrections, hitam, total_policies)
        self.btn_export.setEnabled(bool(corrections))

        pol_count  = len({r["Policy_Number"] for r in corrections})
        entry_count = len(corrections)
        total_amt  = sum(r.get("AMOUNT", 0) for r in corrections if r.get("DT") == "84.1.1.")
        hitam_count = len(hitam)

        msg = (
            f"Hesablama tamamlandı / Расчёт завершён — "
            f"{pol_count} polislər, {entry_count} müxabirləşmələr, "
            f"məbləğ: {total_amt:,.2f}"
        )
        if hitam_count:
            msg += f"  |  Bağlı (hitam): {hitam_count}"
        self.status.showMessage(msg)

    def _on_calc_error(self, error_text: str):
        self.status.showMessage("Xəta / Ошибка")
        QMessageBox.critical(
            self,
            "Hesablama xətası / Ошибка расчёта",
            f"Xəta baş verdi / Произошла ошибка:\n\n{error_text[:800]}",
        )

    def _on_export(self):
        if not self._corrections:
            return

        from core.export import export_to_excel

        default_name = f"korreksiyalar_{self._report_date}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Excel-ə ixrac / Сохранить Excel",
            default_name,
            "Excel Files (*.xlsx)",
        )
        if not path:
            return

        try:
            output_dir  = str(Path(path).parent)
            result_path = export_to_excel(
                self._corrections,
                self._hitam,
                self._total_policies,
                self._report_date,
                output_dir=output_dir,
            )
            # If user specified a custom name, rename
            expected = Path(output_dir) / f"korreksiyalar_{self._report_date}.xlsx"
            target   = Path(path)
            if expected != target and expected.exists():
                expected.rename(target)
                result_path = str(target)

            self._last_export_path = result_path
            self.status.showMessage(f"Saxlandı / Сохранено: {result_path}")

        except Exception as exc:
            QMessageBox.critical(
                self,
                "İxrac xətası / Ошибка экспорта",
                f"Excel faylı yaradılarkən xəta / Ошибка при создании Excel:\n\n{exc}",
            )
