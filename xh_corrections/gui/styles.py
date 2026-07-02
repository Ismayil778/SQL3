"""
QSS stylesheet — Xalq Həyat brand colours.
"""

XH_RED        = "#C8102E"
XH_RED_HOVER  = "#A50D25"
XH_RED_LIGHT  = "#FCECED"
XH_DARK       = "#2D2D2D"
XH_MUTED      = "#6B6B6B"
XH_BG         = "#F5F5F5"
XH_WHITE      = "#FFFFFF"
XH_BORDER     = "#E0E0E0"
XH_GREEN      = "#1D9E75"
XH_AMBER      = "#E8A020"


MAIN_STYLE = f"""
/* ---- Global ---- */
QWidget {{
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 10pt;
    color: {XH_DARK};
    background-color: {XH_BG};
}}

/* ---- Group boxes (card style) ---- */
QGroupBox {{
    background-color: {XH_WHITE};
    border: 1px solid {XH_BORDER};
    border-radius: 8px;
    margin-top: 18px;
    padding: 12px 14px 14px 14px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    top: 2px;
    padding: 0 4px;
    font-weight: bold;
    font-size: 10pt;
    color: {XH_DARK};
}}

/* ---- Primary (red) button ---- */
QPushButton#btn_primary {{
    background-color: {XH_RED};
    color: {XH_WHITE};
    border: none;
    border-radius: 6px;
    padding: 8px 22px;
    font-weight: bold;
    font-size: 10pt;
    min-height: 34px;
}}
QPushButton#btn_primary:hover {{
    background-color: {XH_RED_HOVER};
}}
QPushButton#btn_primary:disabled {{
    background-color: #CCCCCC;
    color: #888888;
}}
QPushButton#btn_primary:pressed {{
    background-color: {XH_RED_HOVER};
}}

/* ---- Secondary button ---- */
QPushButton#btn_secondary {{
    background-color: {XH_WHITE};
    color: {XH_RED};
    border: 1.5px solid {XH_RED};
    border-radius: 6px;
    padding: 6px 18px;
    font-weight: bold;
    min-height: 30px;
}}
QPushButton#btn_secondary:hover {{
    background-color: {XH_RED_LIGHT};
}}
QPushButton#btn_secondary:disabled {{
    color: #AAAAAA;
    border-color: #CCCCCC;
}}

/* ---- Line edits / spinboxes ---- */
QLineEdit, QDateEdit, QSpinBox {{
    background-color: {XH_WHITE};
    border: 1px solid {XH_BORDER};
    border-radius: 5px;
    padding: 5px 8px;
    min-height: 26px;
}}
QLineEdit:focus, QDateEdit:focus {{
    border: 1.5px solid {XH_RED};
}}

/* ---- Progress bar ---- */
QProgressBar {{
    border: 1px solid {XH_BORDER};
    border-radius: 5px;
    background-color: {XH_WHITE};
    height: 14px;
    text-align: center;
    font-size: 9pt;
    color: {XH_DARK};
}}
QProgressBar::chunk {{
    background-color: {XH_RED};
    border-radius: 4px;
}}

/* ---- Table view ---- */
QTableView {{
    background-color: {XH_WHITE};
    border: 1px solid {XH_BORDER};
    border-radius: 6px;
    gridline-color: {XH_BORDER};
    selection-background-color: {XH_RED_LIGHT};
    selection-color: {XH_DARK};
    alternate-background-color: {XH_BG};
}}
QHeaderView::section {{
    background-color: {XH_RED};
    color: {XH_WHITE};
    font-weight: bold;
    padding: 6px;
    border: none;
    border-right: 1px solid #A50D25;
}}
QHeaderView::section:last {{
    border-right: none;
}}

/* ---- Status bar ---- */
QStatusBar {{
    background-color: {XH_WHITE};
    border-top: 1px solid {XH_BORDER};
    color: {XH_MUTED};
    font-size: 9pt;
}}

/* ---- Metric card frames ---- */
QFrame#metric_card {{
    background-color: {XH_WHITE};
    border: 1px solid {XH_BORDER};
    border-radius: 8px;
}}

/* ---- Scrollbar ---- */
QScrollBar:vertical {{
    border: none;
    background: {XH_BG};
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #CCCCCC;
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: #AAAAAA;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""
