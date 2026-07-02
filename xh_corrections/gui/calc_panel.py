"""
Calculation panel — period pickers + calculate button + progress bar.
Requires both conn_1c (Base_1c77) and conn_life (XalqLife) to be set.
Heavy computation runs in a QThread to keep the UI responsive.
"""
from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QPushButton, QDateEdit, QLabel, QProgressBar,
)
from PySide6.QtCore import QDate, QThread, Signal, QObject
from PySide6.QtGui import QFont

from gui.styles import XH_MUTED


class _Worker(QObject):
    finished   = Signal(list, list, int)  # corrections, xitam_list, total_policies
    error      = Signal(str)
    progress   = Signal(int, int)
    status_msg = Signal(str)

    def __init__(self, conn_1c, conn_life, report_date_str: str, period_start_str: str):
        super().__init__()
        self._conn_1c       = conn_1c
        self._conn_life     = conn_life
        self._report_date   = report_date_str
        self._period_start  = period_start_str

    def run(self):
        try:
            from core.policy_loader import (
                load_xmli_policies_from_life,
                load_payment_plans,
                load_recognised_income_from_1c,
            )
            from core.corrections_calc import calculate_corrections
            from core.xitam_detector import load_xitam_policies

            self.status_msg.emit("XalqLife: polislər yüklənir / загрузка полисов...")
            policies = load_xmli_policies_from_life(self._conn_life)
            total_policies = len(policies)

            self.status_msg.emit(
                f"XalqLife: {total_policies} polis — ödəniş planı yüklənir / план платежей..."
            )
            payment_plans = load_payment_plans(self._conn_life)

            self.status_msg.emit("Base_1c77: _1SENTRY sorğusu / запрос к _1SENTRY...")
            recognised = load_recognised_income_from_1c(
                self._conn_1c,
                self._report_date,
                progress_callback=lambda done, total: self.progress.emit(done, total),
            )

            self.status_msg.emit("Korreksiyalar hesablanır / Расчёт корректировок...")
            corrections = calculate_corrections(
                policies, payment_plans, recognised, self._report_date
            )

            self.status_msg.emit("Xitam polisləri yüklənir / Загрузка закрытых полисов...")
            xitam_list = load_xitam_policies(
                self._conn_life, self._period_start, self._report_date
            )

            self.finished.emit(corrections, xitam_list, total_policies)

        except Exception:
            import traceback
            self.error.emit(traceback.format_exc())


class CalcPanel(QGroupBox):
    calculation_done    = Signal(list, list, int, str)  # corrections, xitam, total, report_date
    calculation_error   = Signal(str)
    calculation_started = Signal()

    def __init__(self, parent=None):
        super().__init__("Hesablama / Параметры расчёта", parent)
        self._conn_1c   = None
        self._conn_life = None
        self._thread    = None
        self._worker    = None
        self._report_date  = ""
        self._period_start = ""
        self._build_ui()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setSpacing(10)

        hint = QLabel(
            "Hər iki bağlantı qurulduqdan sonra tarixləri seçin və Hesabla düyməsinə basın. / "
            "После подключения обеих БД выберите период и нажмите Рассчитать."
        )
        hint.setWordWrap(True)
        hint.setFont(QFont("Segoe UI", 9))
        hint.setStyleSheet(f"color: {XH_MUTED};")
        main.addWidget(hint)

        # Date pickers row
        dates_row = QHBoxLayout()

        lbl_start = QLabel("Dövr başlanğıcı / Начало периода:")
        lbl_start.setMinimumWidth(210)
        dates_row.addWidget(lbl_start)

        self.date_start = QDateEdit()
        self.date_start.setDisplayFormat("dd.MM.yyyy")
        # Default: January 1 of current year
        today = QDate.currentDate()
        self.date_start.setDate(QDate(today.year(), 1, 1))
        self.date_start.setCalendarPopup(True)
        self.date_start.setMinimumWidth(130)
        dates_row.addWidget(self.date_start)

        dates_row.addSpacing(20)

        lbl_end = QLabel("Hesab tarixi / Дата расчёта:")
        lbl_end.setMinimumWidth(180)
        dates_row.addWidget(lbl_end)

        self.date_edit = QDateEdit()
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setDate(today)
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setMinimumWidth(130)
        dates_row.addWidget(self.date_edit)

        dates_row.addStretch()
        main.addLayout(dates_row)

        # Calculate button
        self.btn_calc = QPushButton("Hesabla / Рассчитать")
        self.btn_calc.setObjectName("btn_primary")
        self.btn_calc.setEnabled(False)
        self.btn_calc.setMinimumHeight(40)
        self.btn_calc.clicked.connect(self._on_calculate)
        main.addWidget(self.btn_calc)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(16)
        main.addWidget(self.progress_bar)

    def set_connections(self, conn_1c, conn_life):
        self._conn_1c   = conn_1c
        self._conn_life = conn_life
        self._update_btn()

    def clear_connection_1c(self):
        self._conn_1c = None
        self._update_btn()

    def clear_connection_life(self):
        self._conn_life = None
        self._update_btn()

    def _update_btn(self):
        self.btn_calc.setEnabled(
            self._conn_1c is not None and self._conn_life is not None
        )

    def _on_calculate(self):
        if not self._conn_1c or not self._conn_life:
            return

        qd_end   = self.date_edit.date()
        qd_start = self.date_start.date()
        self._report_date  = f"{qd_end.year():04d}{qd_end.month():02d}{qd_end.day():02d}"
        self._period_start = f"{qd_start.year():04d}{qd_start.month():02d}{qd_start.day():02d}"

        self._set_busy(True)
        self.calculation_started.emit()

        self._thread = QThread()
        self._worker = _Worker(
            self._conn_1c, self._conn_life,
            self._report_date, self._period_start,
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.progress.connect(self._on_progress)
        self._worker.status_msg.connect(self._on_status)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_finished)

        self._thread.start()

    def _on_status(self, msg: str):
        self.progress_bar.setFormat(msg[:70])

    def _on_progress(self, done: int, total: int):
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(done)

    def _on_done(self, corrections, xitam_list, total_policies):
        self._set_busy(False)
        self.calculation_done.emit(corrections, xitam_list, total_policies, self._report_date)

    def _on_error(self, msg: str):
        self._set_busy(False)
        self.calculation_error.emit(msg)

    def _on_thread_finished(self):
        self._thread = None
        self._worker = None

    def _set_busy(self, busy: bool):
        self.btn_calc.setEnabled(not busy)
        self.progress_bar.setVisible(busy)
        if busy:
            self.progress_bar.setRange(0, 0)
