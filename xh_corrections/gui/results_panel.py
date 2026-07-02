"""
Results panel — metric cards + filterable table of corrections.
"""
from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QLineEdit, QTableView,
    QSizePolicy, QHeaderView,
)
from PySide6.QtCore import Qt, QSortFilterProxyModel, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QFont, QColor

from gui.styles import XH_RED, XH_WHITE, XH_BORDER, XH_MUTED, XH_DARK, XH_BG


class _CorrectionsModel(QAbstractTableModel):
    HEADERS = ["DT", "KT", "AMOUNT", "Siyasət / Полис", "Müştəri / Клиент", "Ay / Мес."]
    KEY_MAP = ["DT", "KT", "AMOUNT", "Policy_Number", "Client", "Months"]

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
            # Return combined searchable string
            return f"{row.get('Policy_Number','')} {row.get('Client','')}".lower()

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
        model = self.sourceModel()
        idx = model.index(source_row, 0, source_parent)
        combined = model.data(idx, Qt.UserRole) or ""
        return self._filter_text in combined


class _MetricCard(QFrame):
    def __init__(self, title: str, value: str = "—", parent=None):
        super().__init__(parent)
        self.setObjectName("metric_card")
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(72)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)

        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(QFont("Segoe UI", 8))
        self.lbl_title.setStyleSheet(f"color: {XH_MUTED};")
        layout.addWidget(self.lbl_title)

        self.lbl_value = QLabel(value)
        self.lbl_value.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self.lbl_value.setStyleSheet(f"color: {XH_DARK};")
        layout.addWidget(self.lbl_value)

    def set_value(self, value: str):
        self.lbl_value.setText(value)


class ResultsPanel(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Nəticə / Результаты", parent)
        self._all_rows: list[dict] = []
        self._build_ui()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setSpacing(10)

        # --- Metric cards ---
        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)

        self.card_policies  = _MetricCard("Polislər / Полисов")
        self.card_entries   = _MetricCard("Müxabirləşmələr / Проводок")
        self.card_amount    = _MetricCard("Cəmi məbləğ / Сумма")

        cards_row.addWidget(self.card_policies)
        cards_row.addWidget(self.card_entries)
        cards_row.addWidget(self.card_amount)
        main.addLayout(cards_row)

        # --- Filter box ---
        filter_row = QHBoxLayout()
        filter_lbl = QLabel("Axtarış / Поиск:")
        filter_lbl.setStyleSheet(f"color: {XH_MUTED}; font-size: 9pt;")
        filter_row.addWidget(filter_lbl)
        self.le_filter = QLineEdit()
        self.le_filter.setPlaceholderText("Policy nömrəsi və ya müştəri adı / Номер полиса или имя клиента...")
        self.le_filter.setClearButtonEnabled(True)
        self.le_filter.textChanged.connect(self._on_filter)
        filter_row.addWidget(self.le_filter)
        main.addLayout(filter_row)

        # --- Table ---
        self._model = _CorrectionsModel([])
        self._proxy = _PolicyFilter()
        self._proxy.setSourceModel(self._model)
        self._proxy.setSortRole(Qt.DisplayRole)

        self.table = QTableView()
        self.table.setModel(self._proxy)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Interactive)
        hh.setStretchLastSection(False)
        # Default column widths
        col_widths = [100, 100, 110, 175, 260, 70]
        for i, w in enumerate(col_widths):
            self.table.setColumnWidth(i, w)

        main.addWidget(self.table)

    def _on_filter(self, text: str):
        self._proxy.set_filter(text)

    def set_results(self, corrections: list[dict], hitam: list[str], total_policies: int):
        self._all_rows = corrections

        # Metrics
        policies_with_corr = len({r["Policy_Number"] for r in corrections})
        total_amount = sum(r.get("AMOUNT", 0) for r in corrections if r.get("DT") == "84.1.1.")

        self.card_policies.set_value(f"{policies_with_corr:,}")
        self.card_entries.set_value(f"{len(corrections):,}")
        self.card_amount.set_value(f"{total_amount:,.2f}")

        # Table
        self._model.set_rows(sorted(corrections, key=lambda r: r.get("Policy_Number", "")))

    def clear(self):
        self._all_rows = []
        self._model.set_rows([])
        self.card_policies.set_value("—")
        self.card_entries.set_value("—")
        self.card_amount.set_value("—")
