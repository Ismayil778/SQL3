"""
Calculation panel — period pickers + calculate button + progress bar.
Requires both connections (Base_1c77 and XalqLife) AND balances file loaded.
Heavy computation runs in QThread.
"""
from datetime import date as pydate

from PySide6.QtCore import QDate, QObject, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDateEdit, QGroupBox, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QVBoxLayout,
)

from xh_corrections.gui.styles import XH_MUTED, BUTTON_STYLE


class _Worker(QObject):
    finished   = Signal(list, list, int)   # corrections, xitam_list, total_policies
    error      = Signal(str)
    status_msg = Signal(str)

    def __init__(
        self,
        conn_1c,
        conn_life,
        balances: dict,
        period_start_str: str,   # 'YYYYMMDD' (balance snapshot date = period start)
        report_date_str: str,    # 'YYYYMMDD' (report / period end date)
    ):
        super().__init__()
        self._conn_1c          = conn_1c
        self._conn_life        = conn_life
        self._balances         = balances
        self._period_start_str = period_start_str
        self._report_date_str  = report_date_str

    def run(self):
        try:
            from xh_corrections.core.policy_loader import (
                load_xmli_policies_from_life,
                load_payment_plans_summary,
                load_last_reclassifications,
            )
            from xh_corrections.core.corrections_calc import calculate_corrections

            self.status_msg.emit("XalqLife: polislər yüklənir / загрузка полисов...")
            policies = load_xmli_policies_from_life(self._conn_life)
            total    = len(policies)

            self.status_msg.emit(
                f"XalqLife: {total:,} polis — ödəniş planı / план платежей..."
            )
            payment_plans = load_payment_plans_summary(self._conn_life)

            self.status_msg.emit(
                "Base_1c77: son reqlassifikasiya / последняя реклассификация BA→B7..."
            )
            last_reclass = load_last_reclassifications(
                self._conn_1c, self._period_start_str
            )

            self.status_msg.emit("Korreksiyalar hesablanır / Расчёт корректировок...")

            # Parse dates
            ps = self._period_start_str
            rd = self._report_date_str
            period_start = pydate(int(ps[:4]), int(ps[4:6]), int(ps[6:8]))
            period_end   = pydate(int(rd[:4]), int(rd[4:6]), int(rd[6:8]))

            corrections, xitam_list = calculate_corrections(
                policies      = policies,
                balances      = self._balances,
                last_reclass  = last_reclass,
                payment_plans = payment_plans,
                period_start  = period_start,
                period_end    = period_end,
            )

            self.finished.emit(corrections, xitam_list, total)

        except Exception:
            import traceback
            self.error.emit(traceback.format_exc())


class CalcPanel(QGroupBox):
    calculation_done    = Signal(list, list, int, str, str)  # corrections, xitam, total, period_start, report_date
    calculation_error   = Signal(str)
    calculation_started = Signal()

    def __init__(self, parent=None):
        super().__init__("Hesablama / Параметры расчёта", parent)
        self._conn_1c          = None
        self._conn_life        = None
        self._balances: dict   = {}
        self._thread           = None
        self._worker           = None
        self._period_start_str = ""
        self._report_date_str  = ""
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setSpacing(10)

        hint = QLabel(
            "Qalıq faylı yüklənmiş və hər iki bağlantı qurulmuş olmalıdır.  /  "
            "Файл остатков загружен и оба подключения установлены."
        )
        hint.setWordWrap(True)
        hint.setFont(QFont("Segoe UI", 9))
        hint.setStyleSheet(f"color: {XH_MUTED};")
        main.addWidget(hint)

        # Date pickers
        row = QHBoxLayout()

        row.addWidget(QLabel("Başlanğıc tarixi / Начало периода:"))
        self.date_start = QDateEdit()
        self.date_start.setDisplayFormat("dd.MM.yyyy")
        self.date_start.setDate(QDate(2026, 4, 1))
        self.date_start.setCalendarPopup(True)
        self.date_start.setMinimumWidth(120)
        row.addWidget(self.date_start)

        row.addSpacing(20)

        row.addWidget(QLabel("Son tarix / Отчётная дата:"))
        self.date_end = QDateEdit()
        self.date_end.setDisplayFormat("dd.MM.yyyy")
        self.date_end.setDate(QDate(2026, 6, 30))
        self.date_end.setCalendarPopup(True)
        self.date_end.setMinimumWidth(120)
        row.addWidget(self.date_end)

        row.addStretch()
        main.addLayout(row)

        hint2 = QLabel(
            "Başlanğıc tarixi = qalıq faylının tarixi (31.03.2026).  /  "
            "Начало периода = дата файла остатков (31.03.2026)."
        )
        hint2.setWordWrap(True)
        hint2.setStyleSheet(f"color: {XH_MUTED}; font-size: 11px;")
        main.addWidget(hint2)

        # Calculate button
        self.btn_calc = QPushButton("Hesabla / Рассчитать")
        self.btn_calc.setStyleSheet(BUTTON_STYLE)
        self.btn_calc.setEnabled(False)
        self.btn_calc.setMinimumHeight(40)
        self.btn_calc.clicked.connect(self._on_calculate)
        main.addWidget(self.btn_calc)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(16)
        main.addWidget(self.progress_bar)

    # ------------------------------------------------------------------
    def set_connections(self, conn_1c, conn_life):
        self._conn_1c   = conn_1c
        self._conn_life = conn_life
        self._update_btn()

    def set_balances(self, balances: dict):
        self._balances = balances
        self._update_btn()

    def clear_connection_1c(self):
        self._conn_1c = None
        self._update_btn()

    def clear_connection_life(self):
        self._conn_life = None
        self._update_btn()

    def clear_balances(self):
        self._balances = {}
        self._update_btn()

    def _update_btn(self):
        self.btn_calc.setEnabled(
            bool(self._balances)
            and self._conn_1c is not None
            and self._conn_life is not None
        )

    # ------------------------------------------------------------------
    def _on_calculate(self):
        if not self._conn_1c or not self._conn_life or not self._balances:
            return

        qs = self.date_start.date()
        qe = self.date_end.date()
        self._period_start_str = f"{qs.year():04d}{qs.month():02d}{qs.day():02d}"
        self._report_date_str  = f"{qe.year():04d}{qe.month():02d}{qe.day():02d}"

        self._set_busy(True)
        self.calculation_started.emit()

        self._thread = QThread()
        self._worker = _Worker(
            conn_1c          = self._conn_1c,
            conn_life        = self._conn_life,
            balances         = self._balances,
            period_start_str = self._period_start_str,
            report_date_str  = self._report_date_str,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.status_msg.connect(self._on_status)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()

    def _on_status(self, msg: str):
        self.progress_bar.setFormat(msg[:80])

    def _on_done(self, corrections, xitam_list, total):
        self._set_busy(False)
        self.calculation_done.emit(
            corrections, xitam_list, total,
            self._period_start_str, self._report_date_str,
        )

    def _on_error(self, msg: str):
        self._set_busy(False)
        self.calculation_error.emit(msg)

    def _on_thread_finished(self):
        self._thread = None
        self._worker = None

    def _set_busy(self, busy: bool):
        self.btn_calc.setEnabled(not busy and self._update_btn() is None and bool(self._balances))
        self.progress_bar.setVisible(busy)
        if busy:
            self.progress_bar.setRange(0, 0)
            self.progress_bar.setFormat("Yüklənir... / Загрузка...")
