"""
Main application window — Xalq Həyat Korrektəedici Müxabirləşmələr (v3).
Three data sources: Excel balances file + XalqLife + Base_1c77.
"""
from PySide6.QtWidgets import (
    QFileDialog, QGroupBox, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from xh_corrections.gui.styles import XH_RED, XH_WHITE, XH_MUTED, BUTTON_STYLE
from xh_corrections.gui.connection_panel import ConnectionPanel
from xh_corrections.gui.file_panel import FilePanel
from xh_corrections.gui.calc_panel import CalcPanel
from xh_corrections.gui.results_panel import ResultsPanel
from xh_corrections.core.export import export_to_excel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Xalq Həyat — Korrektəedici Müxabirləşmələr")
        self.setFixedWidth(920)

        self._conn_1c   = None
        self._conn_life = None
        self._corrections   : list = []
        self._xitam_list    : list = []
        self._total_policies: int  = 0
        self._period_start  : str  = ""
        self._report_date   : str  = ""

        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        root_vbox = QVBoxLayout(root)
        root_vbox.setContentsMargins(0, 0, 0, 0)
        root_vbox.setSpacing(0)

        # ── Red header ─────────────────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(52)
        header.setStyleSheet(f"background:{XH_RED};")
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(16, 0, 16, 0)

        logo = QLabel("⟨Z⟩")
        logo.setFont(QFont("Segoe UI", 14, QFont.Bold))
        logo.setStyleSheet(f"color:{XH_WHITE};")
        hdr_layout.addWidget(logo)

        title = QLabel("Xalq Həyat — Korrektəedici Müxabirləşmələr")
        title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        title.setStyleSheet(f"color:{XH_WHITE};")
        hdr_layout.addWidget(title)

        hdr_layout.addStretch()
        ver = QLabel("v3.0")
        ver.setStyleSheet(f"color:{XH_WHITE}; opacity:0.7;")
        hdr_layout.addWidget(ver)
        root_vbox.addWidget(header)

        # ── Scrollable content ─────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        content = QWidget()
        content.setStyleSheet("background:#F5F5F5;")
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(14)

        # ── Section 1: Sources ─────────────────────────────────────────
        src_grp = QGroupBox("Mənbə / Источники данных")
        src_row = QHBoxLayout(src_grp)
        src_row.setSpacing(10)

        # 1a: file panel
        self.file_panel = FilePanel()
        self.file_panel.file_loaded.connect(self._on_file_loaded)
        self.file_panel.file_cleared.connect(self._on_file_cleared)
        src_row.addWidget(self.file_panel, 1)

        # 1b: XalqLife
        self.conn_life = ConnectionPanel(
            title="XalqLife (polislər / полисы)",
            default_db="XalqLife",
            settings_prefix="conn_life",
        )
        self.conn_life.connected.connect(self._on_connected_life)
        self.conn_life.disconnected.connect(self._on_disconnected_life)
        src_row.addWidget(self.conn_life, 1)

        # 1c: Base_1c77
        self.conn_1c = ConnectionPanel(
            title="Base_1c77 (reqlassifikasiya / реклассификация)",
            default_db="Base_1c77",
            settings_prefix="conn_1c",
        )
        note_1c = QLabel("Yalnız reqlassifikasiya məlumatları üçün istifadə olunur\n"
                         "Используется только для реклассификаций BA→B7")
        note_1c.setStyleSheet(f"color:{XH_MUTED}; font-size:10px;")
        note_1c.setWordWrap(True)
        # Insert note into conn_1c layout
        self.conn_1c.layout().addWidget(note_1c)
        self.conn_1c.connected.connect(self._on_connected_1c)
        self.conn_1c.disconnected.connect(self._on_disconnected_1c)
        src_row.addWidget(self.conn_1c, 1)

        vbox.addWidget(src_grp)

        # ── Section 2: Calc ────────────────────────────────────────────
        self.calc_panel = CalcPanel()
        self.calc_panel.calculation_done.connect(self._on_calc_done)
        self.calc_panel.calculation_error.connect(self._on_calc_error)
        vbox.addWidget(self.calc_panel)

        # ── Section 3: Results ─────────────────────────────────────────
        self.results_panel = ResultsPanel()
        vbox.addWidget(self.results_panel)

        # ── Export bar ─────────────────────────────────────────────────
        export_row = QHBoxLayout()
        self.btn_export = QPushButton("Excel-ə ixrac / Выгрузить в Excel")
        self.btn_export.setStyleSheet(BUTTON_STYLE)
        self.btn_export.setEnabled(False)
        self.btn_export.setMinimumHeight(36)
        self.btn_export.clicked.connect(self._on_export)
        export_row.addWidget(self.btn_export)

        self.lbl_export = QLabel("")
        self.lbl_export.setStyleSheet(f"color:{XH_MUTED}; font-size:11px;")
        export_row.addWidget(self.lbl_export)
        export_row.addStretch()
        vbox.addLayout(export_row)

        scroll.setWidget(content)
        root_vbox.addWidget(scroll)

    # ------------------------------------------------------------------
    # Connection slots
    # ------------------------------------------------------------------
    def _on_connected_1c(self, conn):
        self._conn_1c = conn
        self._update_connections()

    def _on_disconnected_1c(self):
        self._conn_1c = None
        self._update_connections()

    def _on_connected_life(self, conn):
        self._conn_life = conn
        self._update_connections()

    def _on_disconnected_life(self):
        self._conn_life = None
        self._update_connections()

    def _update_connections(self):
        self.calc_panel.set_connections(self._conn_1c, self._conn_life)

    # ------------------------------------------------------------------
    # File slots
    # ------------------------------------------------------------------
    def _on_file_loaded(self, balances: dict, total: int):
        self.calc_panel.set_balances(balances)

    def _on_file_cleared(self):
        self.calc_panel.clear_balances()

    # ------------------------------------------------------------------
    # Calculation slots
    # ------------------------------------------------------------------
    def _on_calc_done(
        self,
        corrections: list,
        xitam_list: list,
        total_policies: int,
        period_start: str,
        report_date: str,
    ):
        self._corrections    = corrections
        self._xitam_list     = xitam_list
        self._total_policies = total_policies
        self._period_start   = period_start
        self._report_date    = report_date

        self.results_panel.set_results(corrections, xitam_list, total_policies)
        self.btn_export.setEnabled(bool(corrections) or bool(xitam_list))
        self.lbl_export.setText("")

    def _on_calc_error(self, msg: str):
        QMessageBox.critical(self, "Xəta / Ошибка", msg)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Excel-ə ixrac / Сохранить Excel",
            f"korreksiyalar_{self._report_date}.xlsx",
            "Excel files (*.xlsx)",
        )
        if not path:
            return
        try:
            out = export_to_excel(
                corrections      = self._corrections,
                xitam_list       = self._xitam_list,
                total_policies   = self._total_policies,
                period_start_str = self._period_start,
                report_date_str  = self._report_date,
                output_path      = path,
            )
            self.lbl_export.setText(f"✓  {out}")
        except Exception as exc:
            QMessageBox.critical(self, "Xəta / Ошибка", str(exc))
