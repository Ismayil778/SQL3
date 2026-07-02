"""
Main application window — Xalq Həyat Korrektəedici Müxabirləşmələr (v2).
Two-database architecture: Base_1c77 (left) + XalqLife (right).
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QPushButton, QScrollArea,
    QSizePolicy, QMessageBox, QFileDialog, QStatusBar,
)
from PySide6.QtGui import QFont

from gui.styles import MAIN_STYLE, XH_RED, XH_WHITE, XH_BG
from gui.connection_panel import ConnectionPanel
from gui.calc_panel import CalcPanel
from gui.results_panel import ResultsPanel


class HeaderBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(54)
        self.setStyleSheet(f"background-color: {XH_RED};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)

        logo = QLabel("⟨Z⟩")
        logo.setFont(QFont("Segoe UI", 16, QFont.Bold))
        logo.setStyleSheet(f"color: {XH_WHITE}; background: transparent;")
        layout.addWidget(logo)

        layout.addSpacing(10)

        title = QLabel("Xalq Həyat — Korrektəedici Müxabirləşmələr")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title.setStyleSheet(f"color: {XH_WHITE}; background: transparent;")
        layout.addWidget(title)

        layout.addStretch()

        ver = QLabel("v2.0")
        ver.setFont(QFont("Segoe UI", 9))
        ver.setStyleSheet("color: rgba(255,255,255,180); background: transparent;")
        layout.addWidget(ver)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Xalq Həyat — Korrektəedici Müxabirləşmələr")
        self.setFixedWidth(900)
        self.setMinimumHeight(800)
        self.setStyleSheet(MAIN_STYLE)

        self._corrections:    list[dict] = []
        self._xitam_list:     list[dict] = []
        self._total_policies: int        = 0
        self._report_date:    str        = ""
        self._conn_1c                    = None
        self._conn_life                  = None

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

        root.addWidget(HeaderBar())

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

        # --- Section 1: two connection panels side by side ---
        conn_row = QHBoxLayout()
        conn_row.setSpacing(14)

        self.conn_1c = ConnectionPanel(
            title="Base_1c77 — Mühasibat / 1С Бухгалтерия",
            default_db="Base_1c77",
            settings_prefix="conn_1c",
        )
        self.conn_life = ConnectionPanel(
            title="XalqLife — Sığorta sistemi / Система полисов",
            default_db="XalqLife",
            settings_prefix="conn_life",
        )
        conn_row.addWidget(self.conn_1c)
        conn_row.addWidget(self.conn_life)
        layout.addLayout(conn_row)

        # --- Section 2: Calculation panel ---
        self.calc_panel = CalcPanel()
        layout.addWidget(self.calc_panel)

        # --- Section 3: Results ---
        self.results_panel = ResultsPanel()
        self.results_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.results_panel, stretch=1)

        # --- Export button row ---
        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 4, 0, 0)

        self.btn_export = QPushButton("Excel-ə ixrac / Выгрузить в Excel  (3 vərəq / листа)")
        self.btn_export.setObjectName("btn_primary")
        self.btn_export.setEnabled(False)
        self.btn_export.setMinimumHeight(38)
        self.btn_export.setMinimumWidth(300)
        self.btn_export.clicked.connect(self._on_export)
        bottom.addWidget(self.btn_export)
        bottom.addStretch()

        layout.addLayout(bottom)
        root.addWidget(scroll)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Hər iki bazaya bağlanın / Подключитесь к обеим БД")

    # ------------------------------------------------------------------ #
    #  Signal wiring
    # ------------------------------------------------------------------ #

    def _connect_signals(self):
        self.conn_1c.connected.connect(self._on_connected_1c)
        self.conn_1c.disconnected.connect(self._on_disconnected_1c)
        self.conn_life.connected.connect(self._on_connected_life)
        self.conn_life.disconnected.connect(self._on_disconnected_life)

        self.calc_panel.calculation_started.connect(self._on_calc_started)
        self.calc_panel.calculation_done.connect(self._on_calc_done)
        self.calc_panel.calculation_error.connect(self._on_calc_error)

    # ------------------------------------------------------------------ #
    #  Connection slots
    # ------------------------------------------------------------------ #

    def _on_connected_1c(self, conn):
        self._conn_1c = conn
        self._update_connections()
        self.status.showMessage("Base_1c77 bağlandı / подключена")

    def _on_disconnected_1c(self):
        self._conn_1c = None
        self._update_connections()
        self.status.showMessage("Base_1c77 bağlantısı kəsildi / отключена")

    def _on_connected_life(self, conn):
        self._conn_life = conn
        self._update_connections()
        self.status.showMessage("XalqLife bağlandı / подключена")

    def _on_disconnected_life(self):
        self._conn_life = None
        self._update_connections()
        self.status.showMessage("XalqLife bağlantısı kəsildi / отключена")

    def _update_connections(self):
        """Push current connection state into calc panel."""
        if self._conn_1c and self._conn_life:
            self.calc_panel.set_connections(self._conn_1c, self._conn_life)
            self.status.showMessage(
                "Hər iki baza bağlandı — hesablaya bilərsiniz / "
                "Обе БД подключены — можно рассчитывать"
            )
        elif self._conn_1c:
            self.calc_panel.clear_connection_life()
            self.status.showMessage(
                f"Base_1c77 bağlandı. XalqLife gözlənilir / ожидается..."
            )
        elif self._conn_life:
            self.calc_panel.clear_connection_1c()
            self.status.showMessage(
                f"XalqLife bağlandı. Base_1c77 gözlənilir / ожидается..."
            )
        else:
            self.calc_panel.clear_connection_1c()
            self.calc_panel.clear_connection_life()

    # ------------------------------------------------------------------ #
    #  Calculation slots
    # ------------------------------------------------------------------ #

    def _on_calc_started(self):
        self.btn_export.setEnabled(False)
        self.results_panel.clear()
        self.status.showMessage("Yüklənir... / Загрузка данных...")

    def _on_calc_done(
        self,
        corrections: list,
        xitam_list: list,
        total_policies: int,
        report_date: str,
    ):
        self._corrections    = corrections
        self._xitam_list     = xitam_list
        self._total_policies = total_policies
        self._report_date    = report_date

        self.results_panel.set_results(corrections, xitam_list, total_policies)
        self.btn_export.setEnabled(bool(corrections or xitam_list))

        pol_count   = len({r["Policy_Number"] for r in corrections})
        total_amt   = sum(r.get("AMOUNT", 0) for r in corrections if r.get("DT") == "84.1.1.")
        xitam_count = len(xitam_list)

        msg = (
            f"Hesablama tamamlandı / Расчёт завершён — "
            f"{pol_count} polis, {len(corrections)} müxabirləşmə, "
            f"məbləğ: {total_amt:,.2f}"
        )
        if xitam_count:
            msg += f"  |  Xitam: {xitam_count}"
        self.status.showMessage(msg)

    def _on_calc_error(self, error_text: str):
        self.status.showMessage("Xəta / Ошибка")
        QMessageBox.critical(
            self,
            "Hesablama xətası / Ошибка расчёта",
            f"Xəta baş verdi / Произошла ошибка:\n\n{error_text[:800]}",
        )

    # ------------------------------------------------------------------ #
    #  Export
    # ------------------------------------------------------------------ #

    def _on_export(self):
        if not self._corrections and not self._xitam_list:
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
            result_path = export_to_excel(
                self._corrections,
                self._xitam_list,
                self._total_policies,
                self._report_date,
                output_path=path,
            )
            self.status.showMessage(f"Saxlandı / Сохранено: {result_path}")
        except Exception as exc:
            QMessageBox.critical(
                self,
                "İxrac xətası / Ошибка экспорта",
                f"Excel faylı yaradılarkən xəta / Ошибка при создании Excel:\n\n{exc}",
            )
