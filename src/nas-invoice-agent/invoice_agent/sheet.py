"""Append rows to the master .xlsx without corrupting it."""

import logging
import os
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill

log = logging.getLogger(__name__)

COLUMNS = [
    ("processed_at", "Processed At", 20),
    ("file_name", "File Name", 30),
    ("file_path", "File Path", 50),
    ("document_type", "Doc Type", 12),
    ("supplier_name", "Supplier", 28),
    ("supplier_abn", "Supplier ABN", 15),
    ("invoice_number", "Invoice No.", 16),
    ("invoice_date", "Invoice Date", 12),
    ("due_date", "Due Date", 12),
    ("customer_name", "Billed To", 24),
    ("currency", "Currency", 9),
    ("subtotal", "Subtotal", 12),
    ("tax_amount", "Tax (GST)", 12),
    ("total", "Total", 12),
    ("description", "Description", 40),
    ("confidence", "Confidence", 11),
    ("needs_review", "Needs Review", 12),
    ("notes", "Notes", 40),
    ("ocr_pages", "OCR Pages", 10),
    ("sha256", "File Hash", 20),
]
SHEET_NAME = "Invoices"
REVIEW_FILL = PatternFill("solid", start_color="FFF2CC")
MONEY_FIELDS = {"subtotal", "tax_amount", "total"}


class SpreadsheetLocked(Exception):
    pass


def _lock_file(path: Path) -> Path:
    # Excel creates "~$name.xlsx" next to a file it has open.
    return path.with_name("~$" + path.name)


def _new_workbook() -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET_NAME
    ws.append([label for _, label, _ in COLUMNS])
    for i, (_, _, width) in enumerate(COLUMNS, start=1):
        ws.cell(row=1, column=i).font = Font(bold=True)
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = width
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    return wb


def append_rows(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    if _lock_file(path).exists():
        raise SpreadsheetLocked(f"{path.name} is open in Excel; will retry next scan")

    path.parent.mkdir(parents=True, exist_ok=True)
    wb = load_workbook(path) if path.exists() else _new_workbook()
    ws = wb[SHEET_NAME] if SHEET_NAME in wb.sheetnames else wb.active

    for row in rows:
        ws.append([row.get(key) for key, _, _ in COLUMNS])
        r = ws.max_row
        for i, (key, _, _) in enumerate(COLUMNS, start=1):
            if key in MONEY_FIELDS:
                ws.cell(row=r, column=i).number_format = "#,##0.00"
            if row.get("needs_review"):
                ws.cell(row=r, column=i).fill = REVIEW_FILL
    ws.auto_filter.ref = ws.dimensions

    # Write to a temp file then swap it in, so a crash or power cut mid-save can't corrupt the master.
    tmp = path.with_name(f".{path.stem}.tmp.xlsx")
    wb.save(tmp)
    os.replace(tmp, path)
    log.info("Wrote %d row(s) to %s", len(rows), path)
