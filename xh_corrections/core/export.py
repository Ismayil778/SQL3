"""
Export corrections to Excel (openpyxl).

Sheet 1 "Müxabirləşmələr": DT | KT | AMOUNT | Policy_Number
Sheet 2 "Xülasə": summary statistics
"""
from datetime import datetime
from pathlib import Path

import openpyxl
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side, numbers
)
from openpyxl.utils import get_column_letter


XH_RED_HEX    = "C8102E"
XH_WHITE_HEX  = "FFFFFF"
XH_LIGHT_HEX  = "F5F5F5"
XH_HEADER_HEX = "2D2D2D"
XH_BORDER_HEX = "E0E0E0"


def _thin_border(color: str = "CCCCCC") -> Border:
    side = Side(style="thin", color=color)
    return Border(left=side, right=side, top=side, bottom=side)


def _header_fill() -> PatternFill:
    return PatternFill("solid", fgColor=XH_RED_HEX)


def export_to_excel(
    corrections: list[dict],
    hitam_policies: list[str],
    total_policies: int,
    report_date_str: str,   # 'YYYYMMDD'
    output_dir: str = ".",
) -> str:
    """
    Write Excel file and return the absolute path.
    """
    rd = report_date_str
    report_date_fmt = f"{rd[6:8]}.{rd[4:6]}.{rd[:4]}"
    filename = f"korreksiyalar_{report_date_str}.xlsx"
    output_path = Path(output_dir) / filename

    wb = openpyxl.Workbook()

    _write_entries_sheet(wb, corrections, report_date_fmt)
    _write_summary_sheet(wb, corrections, hitam_policies, total_policies, report_date_fmt)

    # Remove default empty sheet if still present
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]

    wb.save(str(output_path))
    return str(output_path.resolve())


def _write_entries_sheet(wb: openpyxl.Workbook, corrections: list[dict], report_date_fmt: str) -> None:
    ws = wb.create_sheet("Müxabirləşmələr")

    headers = ["DT", "KT", "AMOUNT", "Policy_Number", "Müştəri / Клиент", "Ay / Месяцев"]
    col_widths = [14, 14, 16, 22, 38, 14]

    header_font  = Font(name="Calibri", bold=True, color=XH_WHITE_HEX, size=11)
    header_fill  = _header_fill()
    header_align = Alignment(horizontal="center", vertical="center")

    for col_idx, (h, w) in enumerate(zip(headers, col_widths), start=1):
        cell = ws.cell(row=1, column=col_idx, value=h)
        cell.font   = header_font
        cell.fill   = header_fill
        cell.alignment = header_align
        cell.border = _thin_border("AAAAAA")
        ws.column_dimensions[get_column_letter(col_idx)].width = w

    ws.row_dimensions[1].height = 22

    # Sort by policy number
    sorted_corr = sorted(corrections, key=lambda r: r.get("Policy_Number", ""))

    light_fill  = PatternFill("solid", fgColor=XH_LIGHT_HEX)
    white_fill  = PatternFill("solid", fgColor=XH_WHITE_HEX)
    hitam_fill  = PatternFill("solid", fgColor="F5EEEE")
    num_format  = '#,##0.00'
    data_font   = Font(name="Calibri", size=10)
    hitam_font  = Font(name="Calibri", size=10, color="999999", italic=True)
    center_align = Alignment(horizontal="center", vertical="center")
    left_align   = Alignment(horizontal="left",   vertical="center")
    right_align  = Alignment(horizontal="right",  vertical="center")

    for row_idx, row in enumerate(sorted_corr, start=2):
        is_hitam = row.get("Client") == "Xitam"
        if is_hitam:
            fill = hitam_fill
            font = hitam_font
        else:
            fill = white_fill if row_idx % 2 == 0 else light_fill
            font = data_font

        amount_val = row.get("AMOUNT", 0) if not is_hitam else None
        values = [
            row.get("DT", ""),
            row.get("KT", ""),
            amount_val,
            row.get("Policy_Number", ""),
            row.get("Client", ""),
            row.get("Months", "") if not is_hitam else "",
        ]
        aligns = [center_align, center_align, right_align, left_align, left_align, center_align]

        for col_idx, (val, aln) in enumerate(zip(values, aligns), start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font      = font
            cell.fill      = fill
            cell.alignment = aln
            cell.border    = _thin_border(XH_BORDER_HEX)
            if col_idx == 3:   # AMOUNT
                cell.number_format = num_format

    ws.freeze_panes = "A2"
    ws.sheet_view.showGridLines = False


def _write_summary_sheet(
    wb: openpyxl.Workbook,
    corrections: list[dict],
    hitam_policies: list[str],
    total_policies: int,
    report_date_fmt: str,
) -> None:
    ws = wb.create_sheet("Xülasə")

    # Compute stats — exclude hitam marker rows
    active = [r for r in corrections if r.get("Client") != "Xitam"]
    policy_set    = {r["Policy_Number"] for r in active}
    total_entries = len(active)
    total_amount  = sum(r.get("AMOUNT", 0) for r in active if r.get("DT") == "84.1.1.")

    now_fmt = datetime.now().strftime("%d.%m.%Y %H:%M")

    rows = [
        ("Hesab tarixi / Дата расчёта",                  report_date_fmt),
        ("Cəmi polislər / Всего полисов",                total_policies),
        ("Korreksiya olan polislər / Полисов с корректировками", len(policy_set)),
        ("Bağlı polislər (hitam) / Закрытых полисов",   len(hitam_policies)),
        ("Cəmi müxabirləşmələr / Всего проводок",        total_entries),
        ("Cəmi məbləğ / Общая сумма",                    total_amount),
        ("Yaradılma vaxtı / Дата создания",              now_fmt),
    ]

    ws.column_dimensions["A"].width = 48
    ws.column_dimensions["B"].width = 22

    title_font  = Font(name="Calibri", bold=True, color=XH_WHITE_HEX, size=12)
    title_fill  = _header_fill()
    label_font  = Font(name="Calibri", size=10, color="2D2D2D")
    value_font  = Font(name="Calibri", bold=True, size=10)
    label_fill  = PatternFill("solid", fgColor=XH_LIGHT_HEX)
    white_fill  = PatternFill("solid", fgColor=XH_WHITE_HEX)

    # Title row
    title_cell = ws.cell(row=1, column=1, value="Xalq Həyat ASC — Korreksiya Xülasəsi / Сводка корректировок")
    ws.merge_cells("A1:B1")
    title_cell.font      = title_font
    title_cell.fill      = title_fill
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    for i, (label, value) in enumerate(rows, start=2):
        fill = label_fill if i % 2 == 0 else white_fill

        lc = ws.cell(row=i, column=1, value=label)
        lc.font      = label_font
        lc.fill      = fill
        lc.alignment = Alignment(horizontal="left", vertical="center")
        lc.border    = _thin_border(XH_BORDER_HEX)

        vc = ws.cell(row=i, column=2, value=value)
        vc.font      = value_font
        vc.fill      = fill
        vc.alignment = Alignment(horizontal="right", vertical="center")
        vc.border    = _thin_border(XH_BORDER_HEX)
        if isinstance(value, float):
            vc.number_format = '#,##0.00'

        ws.row_dimensions[i].height = 20

    ws.sheet_view.showGridLines = False
