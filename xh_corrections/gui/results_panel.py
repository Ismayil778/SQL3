"""
Results panel — metric cards + corrections table + xitam (closed policies) table.
"""
from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QLineEdit, QTableView,
    QHeaderView, QSizePolicy,
)
from PySide6.QtCore import Qt, QSortFilterProxyModel, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QFont, QColor

from gui.styles import XH_RED, XH_MUTED, XH_DARK, XH_AMBER


# ---------------------------------------------------------------------------
# Corrections table model
# ---------------------------------------------------------------------------

class _CorrectionsModel(QAbstractTableModel):
    HEADERS = ["DT", "KT", "AMOUNT", "Siyasət / Полис", "Ay / Мес."]
    KEY_MAP = ["DT", "KT", "AMOUNT", "Policy_Number", "Months"]

    def __init__(self, rows: list[dict], parent=None):
        super().__init__(parent)
        self._rows = rows

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        key = self.KEY_MAP[index.column()]

        if role == Qt.DisplayRole:
            val = row.get(key, "")
            if key == "AMOUNT":
                return f"{val:,.2f}" if isinstance(val, (int, float)) else str(val)
            return str(val) if val is not None else ""

        if role == Qt.TextAlignmentRole:
            if key == "AMOUNT":
                return Qt.AlignRight | Qt.AlignVCenter
            if key in ("DT", "KT", "Months"):
                return Qt.AlignCenter | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        if role == Qt.ForegroundRole:
            if key == "DT" and row.get("DT") == "84.1.1.":
                return QColor(XH_RED)
            if key == "AMOUNT":
                return QColor("#1D5C8A")

        if role == Qt.UserRole:
            return str(row.get("Policy_Number", "")).lower()

        return None

    def set_rows(self, rows: list[dict]):
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()


class _PolicyFilter(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._filter_text = ""

    def set_filter(self, text: str):
        self._filter_text = text.lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if not self._filter_text:
            return True
        idx = self.sourceModel().index(source_row, 0, source_parent)
        return self._filter_text in (self.sourceModel().data(idx, Qt.UserRole) or "")


# ---------------------------------------------------------------------------
# Xitam table model
# ---------------------------------------------------------------------------

class _XitamModel(QAbstractTableModel):
    HEADERS = ["Siyasət / Полис", "Bağlanma tarixi / Дата закрытия", "AMOUNT (əl ilə / вручную)"]
    KEY_MAP = ["policy_number", "policy_complete_date", "_amount_placeholder"]

    def __init__(self, rows: list[dict], parent=None):
        super().__init__(parent)
        self._rows = rows

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row  = self._rows[index.row()]
        key  = self.KEY_MAP[index.column()]
        col  = index.column()

        if role == Qt.DisplayRole:
            if col == 2:
                return ""   # AMOUNT always empty in GUI — fill in Excel
            val = row.get(key)
            if val is None:
                return ""
            if hasattr(val, "strftime"):
                return val.strftime("%d.%m.%Y")
            return str(val)

        if role == Qt.TextAlignmentRole:
            if col in (1, 2):
                return Qt.AlignCenter | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        if role == Qt.BackgroundRole:
            return QColor("#FFF3CD")   # amber tint for all xitam rows

        if role == Qt.ForegroundRole:
            if col == 2:
                return QColor(XH_MUTED)

        return None

    def set_rows(self, rows: list[dict]):
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()


# ---------------------------------------------------------------------------
# Metric card widget
# ---------------------------------------------------------------------------

class _MetricCard(QFrame):
    def __init__(self, title: str, value: str = "—", parent=None):
        super().__init__(parent)
        self.setObjectName("metric_card")
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(70)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)

        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(QFont("Segoe UI", 8))
        self.lbl_title.setStyleSheet(f"color: {XH_MUTED};")
        layout.addWidget(self.lbl_title)

        self.lbl_value = QLabel(value)
        self.lbl_value.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.lbl_value.setStyleSheet(f"color: {XH_DARK};")
        layout.addWidget(self.lbl_value)

    def set_value(self, value: str):
        self.lbl_value.setText(value)


# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------

def _make_table(model) -> QTableView:
    tv = QTableView()
    tv.setModel(model)
    tv.setSortingEnabled(True)
    tv.setAlternatingRowColors(False)
    tv.setSelectionBehavior(QTableView.SelectRows)
    tv.setEditTriggers(QTableView.NoEditTriggers)
    tv.verticalHeader().setVisible(False)
    tv.setShowGrid(True)
    tv.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    hh = tv.horizontalHeader()
    hh.setSectionResizeMode(QHeaderView.Interactive)
    hh.setStretchLastSection(True)
    return tv


class ResultsPanel(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Nəticə / Результаты", parent)
        self._build_ui()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setSpacing(12)

        # --- Metric cards ---
        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)
        self.card_policies = _MetricCard("Korreksiya / Aktiv (XalqLife)")
        self.card_entries  = _MetricCard("Müxabirləşmələr / Проводок")
        self.card_amount   = _MetricCard("Cəmi məbləğ / Сумма (84.1.1.)")
        self.card_xitam    = _MetricCard("Xitam / Закрытых")
        cards_row.addWidget(self.card_policies)
        cards_row.addWidget(self.card_entries)
        cards_row.addWidget(self.card_amount)
        cards_row.addWidget(self.card_xitam)
        main.addLayout(cards_row)

        # --- Corrections table group ---
        corr_group = QGroupBox("Korrektəedici müxabirləşmələr (3-4 növ) / Корректировки (тип 3-4)")
        corr_layout = QVBoxLayout(corr_group)
        corr_layout.setSpacing(6)

        filter_row = QHBoxLayout()
        filter_lbl = QLabel("Axtarış / Поиск:")
        filter_lbl.setStyleSheet(f"color: {XH_MUTED}; font-size: 9pt;")
        filter_row.addWidget(filter_lbl)
        self.le_filter = QLineEdit()
        self.le_filter.setPlaceholderText("Policy nömrəsi / Номер полиса...")
        self.le_filter.setClearButtonEnabled(True)
        self.le_filter.textChanged.connect(self._on_filter)
        filter_row.addWidget(self.le_filter)
        corr_layout.addLayout(filter_row)

        self._corr_model = _CorrectionsModel([])
        self._corr_proxy = _PolicyFilter()
        self._corr_proxy.setSourceModel(self._corr_model)
        self._corr_proxy.setSortRole(Qt.DisplayRole)

        self.corr_table = _make_table(self._corr_proxy)
        col_widths = [100, 100, 120, 190, 70]
        for i, w in enumerate(col_widths):
            self.corr_table.setColumnWidth(i, w)
        self.corr_table.setMinimumHeight(200)
        corr_layout.addWidget(self.corr_table)

        main.addWidget(corr_group, stretch=3)

        # --- Xitam table group ---
        xitam_group = QGroupBox("Bağlı polislər — Xitam / Закрытые полисы")
        xitam_group.setStyleSheet(
            f"QGroupBox {{ border: 1px solid {XH_AMBER}; }}"
            f"QGroupBox::title {{ color: #7B5A00; }}"
        )
        xitam_layout = QVBoxLayout(xitam_group)

        xitam_note = QLabel(
            "AMOUNT sütunu Excel-də əl ilə doldurulmalıdır — məbləği XalqLife-dan götürün. / "
            "Столбец AMOUNT заполняется вручную в Excel из системы XalqLife."
        )
        xitam_note.setWordWrap(True)
        xitam_note.setFont(QFont("Segoe UI", 9))
        xitam_note.setStyleSheet("color: #7B5A00; background: #FFF3CD; padding: 4px 8px; border-radius: 4px;")
        xitam_layout.addWidget(xitam_note)

        self._xitam_model = _XitamModel([])
        self.xitam_table  = _make_table(self._xitam_model)
        xitam_col_widths  = [220, 200, 180]
        for i, w in enumerate(xitam_col_widths):
            self.xitam_table.setColumnWidth(i, w)
        self.xitam_table.setMinimumHeight(120)
        xitam_layout.addWidget(self.xitam_table)

        main.addWidget(xitam_group, stretch=1)

    def _on_filter(self, text: str):
        self._corr_proxy.set_filter(text)

    def set_results(
        self,
        corrections: list[dict],
        xitam_list: list[dict],
        total_policies: int,
    ):
        policy_set   = {r["Policy_Number"] for r in corrections}
        total_amount = sum(r.get("AMOUNT", 0) for r in corrections if r.get("DT") == "84.1.1.")

        self.card_policies.set_value(f"{len(policy_set):,} / {total_policies:,}")
        self.card_entries.set_value(f"{len(corrections):,}")
        self.card_amount.set_value(f"{total_amount:,.2f}")
        self.card_xitam.set_value(f"{len(xitam_list):,}")

        self._corr_model.set_rows(
            sorted(corrections, key=lambda r: r.get("Policy_Number", ""))
        )
        self._xitam_model.set_rows(xitam_list)

    def clear(self):
        self._corr_model.set_rows([])
        self._xitam_model.set_rows([])
        self.card_policies.set_value("—")
        self.card_entries.set_value("—")
        self.card_amount.set_value("—")
        self.card_xitam.set_value("—")
