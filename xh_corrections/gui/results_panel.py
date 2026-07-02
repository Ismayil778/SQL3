"""
Results panel — metric cards + corrections table (Types 1-4) + xitam table.
"""
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QTableView, QVBoxLayout, QWidget,
)

from xh_corrections.gui.styles import (
    XH_RED, XH_AMBER, XH_DARK, XH_MUTED, XH_BG, XH_WHITE,
    INPUT_STYLE,
)

_AMBER_BG = QColor("#FFF9E6")


# ---------------------------------------------------------------------------
# Model: corrections (Types 1-4)
# ---------------------------------------------------------------------------

class _CorrectionsModel(QAbstractTableModel):
    _COLS = ["DT", "KT", "AMOUNT", "Policy_Number", "Tip / Тип"]

    def __init__(self, rows: list[dict] = None):
        super().__init__()
        self._rows = rows or []

    def reset_data(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return len(self._COLS)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._rows):
            return None
        row = self._rows[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return row.get("DT", "")
            if col == 1:
                return row.get("KT", "")
            if col == 2:
                v = row.get("AMOUNT")
                return f"{v:,.2f}" if v is not None else ""
            if col == 3:
                return row.get("Policy_Number", "")
            if col == 4:
                return row.get("Type", "")
        if role == Qt.TextAlignmentRole:
            if col == 2:
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._COLS[section]
        return None


# ---------------------------------------------------------------------------
# Model: xitam
# ---------------------------------------------------------------------------

class _XitamModel(QAbstractTableModel):
    _COLS = ["Policy_Number", "Xitam tarixi", "DT", "KT", "AMOUNT (əl ilə / вручную)"]

    def __init__(self, rows: list[dict] = None):
        super().__init__()
        self._rows = rows or []

    def reset_data(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return len(self._COLS)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._rows):
            return None
        row = self._rows[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            keys = ["Policy_Number", "Xitam tarixi", "DT", "KT", "AMOUNT"]
            val = row.get(keys[col], "")
            return "" if val is None else str(val)
        if role == Qt.BackgroundRole:
            return QBrush(_AMBER_BG)
        if role == Qt.TextAlignmentRole:
            return Qt.AlignLeft | Qt.AlignVCenter
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._COLS[section]
        return None


# ---------------------------------------------------------------------------
# Metric card
# ---------------------------------------------------------------------------

class _MetricCard(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(70)
        self.setStyleSheet(
            f"background:{XH_WHITE}; border:1px solid #E0E0E0; border-radius:6px;"
        )
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(12, 8, 12, 8)
        vbox.setSpacing(2)

        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(f"color:{XH_MUTED}; font-size:11px; border:none;")
        vbox.addWidget(self._title_lbl)

        self._value_lbl = QLabel("—")
        self._value_lbl.setStyleSheet(f"color:{XH_DARK}; font-size:18px; font-weight:bold; border:none;")
        vbox.addWidget(self._value_lbl)

    def set_value(self, v):
        self._value_lbl.setText(str(v))


# ---------------------------------------------------------------------------
# Results panel
# ---------------------------------------------------------------------------

class ResultsPanel(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Nəticə / Результаты", parent)
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        vbox = QVBoxLayout(self)
        vbox.setSpacing(12)

        # Metric cards
        cards_row = QHBoxLayout()
        self._card_policies  = _MetricCard("Polislər / Полисов с корр.")
        self._card_xitam     = _MetricCard("Xitam / Хитамов")
        self._card_entries   = _MetricCard("Müxabirləşmələr / Проводок")
        self._card_amount    = _MetricCard("Cəmi məbləğ (Tip 1-2) / Сумма")
        for c in [self._card_policies, self._card_xitam,
                  self._card_entries, self._card_amount]:
            cards_row.addWidget(c)
        vbox.addLayout(cards_row)

        # ── Corrections table ───────────────────────────────────────────
        grp_corr = QGroupBox("Korrektəedici müxabirləşmələr (Tip 1-4) / Корректировки")
        grp_corr.setStyleSheet(f"QGroupBox {{ border:1px solid #E0E0E0; border-radius:4px; }}")
        corr_vbox = QVBoxLayout(grp_corr)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Axtarış / Поиск:"))
        self._search = QLineEdit()
        self._search.setPlaceholderText("Policy nömrəsi / Номер полиса...")
        self._search.setStyleSheet(INPUT_STYLE)
        self._search.textChanged.connect(self._on_search)
        search_row.addWidget(self._search)
        corr_vbox.addLayout(search_row)

        self._corr_model = _CorrectionsModel()
        self._corr_proxy = QSortFilterProxyModel()
        self._corr_proxy.setSourceModel(self._corr_model)
        self._corr_proxy.setFilterKeyColumn(3)
        self._corr_proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)

        self._corr_view = QTableView()
        self._corr_view.setModel(self._corr_proxy)
        self._corr_view.setSortingEnabled(True)
        self._corr_view.setAlternatingRowColors(False)
        self._corr_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._corr_view.setMinimumHeight(220)
        corr_vbox.addWidget(self._corr_view)
        vbox.addWidget(grp_corr)

        # ── Xitam table ─────────────────────────────────────────────────
        grp_xitam = QGroupBox("Bağlı polislər — Xitam / Закрытые полисы")
        grp_xitam.setStyleSheet(
            f"QGroupBox {{ border:1px solid {XH_AMBER}; border-radius:4px; }}"
        )
        xitam_vbox = QVBoxLayout(grp_xitam)

        note = QLabel(
            "AMOUNT sütunu Excel-də əl ilə doldurulmalıdır — məbləği XalqLife-dan götürün.  /  "
            "Столбец AMOUNT заполняется вручную в Excel из системы XalqLife."
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            f"background:#FFF3CD; color:#8B6914; padding:6px; "
            f"border-radius:4px; font-size:11px;"
        )
        xitam_vbox.addWidget(note)

        self._xitam_model = _XitamModel()
        self._xitam_view  = QTableView()
        self._xitam_view.setModel(self._xitam_model)
        self._xitam_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._xitam_view.setMinimumHeight(160)
        xitam_vbox.addWidget(self._xitam_view)
        vbox.addWidget(grp_xitam)

    # ------------------------------------------------------------------
    def set_results(
        self,
        corrections: list[dict],
        xitam_list: list[dict],
        total_policies: int,
    ) -> None:
        self._corr_model.reset_data(corrections)
        self._xitam_model.reset_data(xitam_list)

        policy_set = {r["Policy_Number"] for r in corrections if r.get("Policy_Number")}
        amount_12  = sum(r["AMOUNT"] for r in corrections
                         if r.get("Type") in ("1", "2") and r.get("AMOUNT"))

        self._card_policies.set_value(f"{len(policy_set):,}")
        self._card_xitam.set_value(f"{len(xitam_list):,}")
        self._card_entries.set_value(f"{len(corrections):,}")
        self._card_amount.set_value(f"{amount_12:,.2f}")

    def clear(self) -> None:
        self._corr_model.reset_data([])
        self._xitam_model.reset_data([])
        for c in [self._card_policies, self._card_xitam,
                  self._card_entries, self._card_amount]:
            c.set_value("—")

    def _on_search(self, text: str) -> None:
        self._corr_proxy.setFilterFixedString(text)
