"""
Exports calculation results to Excel (3 sheets).

Sheet 1 "Müxabirləşmələr" — Types 1-4 correction entries
Sheet 2 "Xitam"            — Closed policies, AMOUNT blank for manual fill
Sheet 3 "Xülasə"           — Summary statistics
"""
import os
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

_RED      = "C8102E"
_WHITE    = "FFFFFF"
_GREY     = "F5F5F5"
_AMBER    = "FFF9E6"
_AMBER_H  = "8B6914"


def export_to_excel(
    corrections: list[dict],
    xitam_list: list[dict],
    total_policies: int,
    period_start_str: str,   # 'YYYYMMDD'
    report_date_str: str,    # 'YYYYMMDD'
    output_path: str = "",
) -> str:
    """Write results to Excel. Returns output file path."""
    if not output_path:
        output_path = os.path.join(
            os.path.expanduser("~"),
            "Desktop",
            f"korreksiyalar_{report_date_str}.xlsx",
        )

    wb = Workbook()
    _write_entries_sheet(wb, corrections)
    _write_xitam_sheet(wb, xitam_list)
    _write_summary_sheet(wb, corrections, xitam_list, total_policies,
                         period_start_str, report_date_str)

    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]

    wb.save(output_path)
    return output_path


# ---------------------------------------------------------------------------
# Sheet 1 — Müxabirləşmələr
# ---------------------------------------------------------------------------

def _write_entries_sheet(wb: Workbook, corrections: list[dict]) -> None:
    ws = wb.create_sheet("Müxabirləşmələr")

    headers = ["DT", "KT", "AMOUNT", "Policy_Number"]
    _header_row(ws, headers)

    fill_w = PatternFill("solid", fgColor=_WHITE)
    fill_g = PatternFill("solid", fgColor=_GREY)

    for i, row in enumerate(
        sorted(corrections, key=lambda r: r.get("Policy_Number", ""))
    ):
        ws.append([
            row.get("DT", ""),
            row.get("KT", ""),
            row.get("AMOUNT"),
            row.get("Policy_Number", ""),
        ])
        r = ws.max_row
        fill = fill_w if i % 2 == 0 else fill_g
        for c in range(1, 5):
            cell = ws.cell(row=r, column=c)
            cell.fill = fill
            cell.alignment = Alignment(horizontal="left")
        ws.cell(row=r, column=3).number_format = '#,##0.00'

    _auto_width(ws)


# ---------------------------------------------------------------------------
# Sheet 2 — Xitam
# ---------------------------------------------------------------------------

def _write_xitam_sheet(wb: Workbook, xitam_list: list[dict]) -> None:
    ws = wb.create_sheet("Xitam")

    note = ws.cell(row=1, column=1,
                   value=("Xitam məbləğləri XalqLife sistemindən əl ilə doldurulur  /  "
                          "Суммы хитам заполняются вручную из системы XalqLife"))
    note.font = Font(italic=True, color=_AMBER_H, size=10)
    ws.merge_cells("A1:E1")
    ws.row_dimensions[1].height = 20

    headers = ["Policy_Number", "Xitam tarixi", "DT", "KT", "AMOUNT (əl ilə / вручную)"]
    _header_row(ws, headers, start_row=2)

    fill_a = PatternFill("solid", fgColor=_AMBER.lstrip("#"))

    for row in xitam_list:
        ws.append([
            row.get("Policy_Number", ""),
            row.get("Xitam tarixi", ""),
            row.get("DT", ""),
            row.get("KT", ""),
            None,   # intentionally blank
        ])
        r = ws.max_row
        for c in range(1, 6):
            cell = ws.cell(row=r, column=c)
            cell.fill = fill_a
        ws.cell(row=r, column=5).number_format = '#,##0.00'

    _auto_width(ws)


# ---------------------------------------------------------------------------
# Sheet 3 — Xülasə
# ---------------------------------------------------------------------------

def _write_summary_sheet(
    wb: Workbook,
    corrections: list[dict],
    xitam_list: list[dict],
    total_policies: int,
    period_start_str: str,
    report_date_str: str,
) -> None:
    ws = wb.create_sheet("Xülasə")

    def _fmt(s: str) -> str:
        return f"{s[6:8]}.{s[4:6]}.{s[:4]}" if len(s) == 8 else s

    policy_set = {r["Policy_Number"] for r in corrections if r.get("Policy_Number")}
    amount_12  = sum(r["AMOUNT"] for r in corrections
                     if r.get("Type") in ("1", "2") and r.get("AMOUNT"))
    amount_34  = sum(r["AMOUNT"] for r in corrections
                     if r.get("Type") in ("3", "4") and r.get("AMOUNT"))

    rows = [
        ("Başlanğıc tarixi / Начало периода",           _fmt(period_start_str)),
        ("Hesab tarixi / Отчётная дата",                 _fmt(report_date_str)),
        ("Cəmi XMLI polislər / Всего XMLI полисов",      total_policies),
        ("Korreksiya olan polislər / С корректировками", len(policy_set)),
        ("Xitam olan polislər / Хитамов",                len(xitam_list)),
        ("Cəmi müxabirləşmələr / Всего проводок",        len(corrections)),
        ("Cəmi məbləğ (Tip 1-2) / Сумма Типов 1-2",     round(amount_12, 2)),
        ("Cəmi məbləğ (Tip 3-4) / Сумма Типов 3-4",     round(amount_34, 2)),
        ("Yaradılma vaxtı / Создан",                     datetime.now().strftime("%d.%m.%Y %H:%M")),
    ]

    _header_row(ws, ["Parametr / Параметр", "Dəyər / Значение"])

    fill_w = PatternFill("solid", fgColor=_WHITE)
    fill_g = PatternFill("solid", fgColor=_GREY)
    for i, (param, val) in enumerate(rows):
        ws.append([param, val])
        r = ws.max_row
        fill = fill_w if i % 2 == 0 else fill_g
        for c in range(1, 3):
            ws.cell(row=r, column=c).fill = fill
        if isinstance(val, float):
            ws.cell(row=r, column=2).number_format = '#,##0.00'

    ws.column_dimensions["A"].width = 52
    ws.column_dimensions["B"].width = 24


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _header_row(ws, headers: list[str], start_row: int | None = None) -> None:
    if start_row:
        for c, h in enumerate(headers, 1):
            _hdr_cell(ws.cell(row=start_row, column=c, value=h))
    else:
        ws.append(headers)
        r = ws.max_row
        for c in range(1, len(headers) + 1):
            _hdr_cell(ws.cell(row=r, column=c))


def _hdr_cell(cell) -> None:
    cell.fill      = PatternFill("solid", fgColor=_RED)
    cell.font      = Font(bold=True, color=_WHITE)
    cell.alignment = Alignment(horizontal="center")


def _auto_width(ws, mn: int = 10, mx: int = 50) -> None:
    for col in ws.columns:
        w = mn
        for cell in col:
            if cell.value:
                w = max(w, min(len(str(cell.value)) + 2, mx))
        ws.column_dimensions[get_column_letter(col[0].column)].width = w
