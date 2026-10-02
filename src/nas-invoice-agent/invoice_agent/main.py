"""Entry point: scan, OCR, extract, write. Loops forever unless SCAN_INTERVAL_SECONDS=0."""

import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from . import config, ocr, scanner, sheet
from .extract import ExtractionError, Extractor, Invoice
from .state import State

log = logging.getLogger("invoice_agent")
_stop = False


def _handle_stop(signum, _frame):
    global _stop
    log.info("Received signal %s, finishing current file then stopping", signum)
    _stop = True


def build_row(path: Path, sha256: str, pdf: ocr.PdfText, invoice: Invoice) -> dict:
    data = invoice.model_dump()
    missing_key_field = any(data[k] is None for k in ("supplier_name", "invoice_date", "total"))
    totals_mismatch = (
        data["subtotal"] is not None
        and data["tax_amount"] is not None
        and data["total"] is not None
        and abs(data["subtotal"] + data["tax_amount"] - data["total"]) > 0.02
    )
    notes = data["notes"] or ""
    if totals_mismatch:
        notes = (notes + " | " if notes else "") + "Subtotal + tax does not equal total"
    if pdf.page_count > pdf.pages_read:
        notes = (notes + " | " if notes else "") + f"Only first {pdf.pages_read} of {pdf.page_count} pages read"
    return {
        **data,
        "notes": notes or None,
        "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "file_name": path.name,
        "file_path": str(path),
        "ocr_pages": pdf.ocr_pages,
        "sha256": sha256[:16],
        "needs_review": "YES" if (invoice.confidence == "low" or missing_key_field or totals_mismatch) else "",
    }


def run_once(settings: config.Settings, state: State, extractor: Extractor) -> None:
    processed = 0
    for path in scanner.find_pdfs(settings.scan_paths, settings.exclude_dirs, settings.min_file_age):
        if _stop or processed >= settings.max_files_per_run:
            break
        try:
            sha = scanner.file_hash(path)
        except OSError as e:
            log.warning("Cannot read %s: %s", path, e)
            continue
        if not state.should_process(sha, settings.max_attempts):
            continue

        log.info("Processing %s", path)
        try:
            pdf = ocr.extract_text(path, settings.max_pages, settings.ocr_dpi, settings.ocr_lang, settings.min_text_chars)
            invoice = extractor.extract(pdf.text, path.name)
            state.mark_extracted(sha, path, build_row(path, sha, pdf, invoice))
        except ExtractionError as e:
            log.warning("Could not extract %s: %s", path, e)
            state.mark_error(sha, path, str(e))
        except Exception as e:  # keep going: one bad PDF must not stop the whole scan
            log.exception("Failed on %s", path)
            state.mark_error(sha, path, f"{type(e).__name__}: {e}")
        processed += 1

    flush(settings, state)
    log.info("Scan done: %d new file(s) processed", processed)


def flush(settings: config.Settings, state: State) -> None:
    pending = state.pending_rows()
    if not pending:
        return
    try:
        sheet.append_rows(settings.spreadsheet_path, [row for _, row in pending])
        state.mark_written([sha for sha, _ in pending])
    except sheet.SpreadsheetLocked as e:
        log.warning("%s (%d row(s) queued)", e, len(pending))
    except PermissionError as e:
        log.warning("Spreadsheet not writable, %d row(s) queued: %s", len(pending), e)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    settings = config.load()
    state = State(settings.state_db_path)
    extractor = Extractor(settings.model, settings.effort, settings.max_text_chars)
    log.info("Scanning %s every %ss -> %s", [str(p) for p in settings.scan_paths], settings.scan_interval, settings.spreadsheet_path)

    while True:
        run_once(settings, state, extractor)
        if settings.scan_interval <= 0 or _stop:
            return 0
        for _ in range(settings.scan_interval):
            if _stop:
                return 0
            time.sleep(1)


if __name__ == "__main__":
    sys.exit(main())
