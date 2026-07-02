"""
Calculation panel — date picker + calculate button + progress bar.
Runs the heavy computation in a QThread to keep the UI responsive.
"""
from datetime import date as dt_date
from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QPushButton, QDateEdit, QLabel, QProgressBar,
)
from PySide6.QtCore import Qt, QDate, QThread, Signal, QObject
from PySide6.QtGui import QFont

from gui.styles import XH_MUTED


class _Worker(QObject):
    finished   = Signal(list, list, int)  # corrections, hitam, total_policies
    error      = Signal(str)
    progress   = Signal(int, int)         # batch_done, total_batches

    def __init__(self, conn, report_date_str: str):
        super().__init__()
        self._conn = conn
        self._report_date = report_date_str

    def run(self):
        try:
            from core.policy_loader import load_all_policies, load_entries_for_policies
            from core.corrections_calc import calculate_corrections

            policies = load_all_policies(self._conn)
            total_policies = len(policies)

            entries_by_policy = load_entries_for_policies(
                self._conn, policies, self._report_date,
                progress_callback=lambda done, total: self.progress.emit(done, total),
            )

            corrections, hitam = calculate_corrections(
                policies, entries_by_policy, self._report_date
            )
            self.finished.emit(corrections, hitam, total_policies)

        except Exception as exc:
            import traceback
            self.error.emit(traceback.format_exc())


class CalcPanel(QGroupBox):
    calculation_done   = Signal(list, list, int, str)  # corrections, hitam, total, report_date
    calculation_error  = Signal(str)
    calculation_started = Signal()

    def __init__(self, parent=None):
        super().__init__("Hesablama / Параметры расчёта", parent)
        self._conn = None
        self._thread = None
        self._worker = None
        self._report_date = ""
        self._build_ui()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setSpacing(10)

        # Date picker row
        date_row = QHBoxLayout()
        lbl = QLabel("Hesab tarixi / Дата расчёта:")
        lbl.setMinimumWidth(190)
        date_row.addWidget(lbl)

        self.date_edit = QDateEdit()
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setMinimumWidth(130)
        date_row.addWidget(self.date_edit)
        date_row.addStretch()
        main.addLayout(date_row)

        # Hint label
        hint = QLabel(
            "Будут сгенерированы проводки за все непроведённые месяцы "
            "по каждому полису до указанной даты включительно."
        )
        hint.setWordWrap(True)
        hint.setFont(QFont("Segoe UI", 9))
        hint.setStyleSheet(f"color: {XH_MUTED};")
        main.addWidget(hint)

        # Calculate button
        self.btn_calc = QPushButton("Hesabla / Рассчитать")
        self.btn_calc.setObjectName("btn_primary")
        self.btn_calc.setEnabled(False)
        self.btn_calc.setMinimumHeight(40)
        self.btn_calc.clicked.connect(self._on_calculate)
        main.addWidget(self.btn_calc)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)   # indeterminate
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(16)
        main.addWidget(self.progress_bar)

    def set_connection(self, conn):
        self._conn = conn
        self.btn_calc.setEnabled(conn is not None)

    def clear_connection(self):
        self._conn = None
        self.btn_calc.setEnabled(False)

    def _on_calculate(self):
        if not self._conn:
            return

        qdate  = self.date_edit.date()
        self._report_date = f"{qdate.year():04d}{qdate.month():02d}{qdate.day():02d}"

        self._set_busy(True)
        self.calculation_started.emit()

        self._thread = QThread()
        self._worker = _Worker(self._conn, self._report_date)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_finished)

        self._thread.start()

    def _on_progress(self, done: int, total: int):
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(done)

    def _on_done(self, corrections, hitam, total_policies):
        self._set_busy(False)
        self.calculation_done.emit(corrections, hitam, total_policies, self._report_date)

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
            self.progress_bar.setRange(0, 0)   # indeterminate until first progress signal
