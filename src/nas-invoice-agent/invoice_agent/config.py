"""Settings, read from environment variables so the same image runs on any NAS."""

import os
from dataclasses import dataclass
from pathlib import Path


def _list(name: str, default: str) -> list[str]:
    return [p.strip() for p in os.environ.get(name, default).split(",") if p.strip()]


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


@dataclass(frozen=True)
class Settings:
    scan_paths: list[Path]
    exclude_dirs: list[str]
    spreadsheet_path: Path
    state_db_path: Path
    scan_interval: int
    min_file_age: int
    max_files_per_run: int
    max_attempts: int
    max_pages: int
    ocr_dpi: int
    ocr_lang: str
    min_text_chars: int
    model: str
    effort: str
    max_text_chars: int


def load() -> Settings:
    return Settings(
        # Folders to scan (comma-separated). Inside Docker these are your mounted NAS shares.
        scan_paths=[Path(p) for p in _list("SCAN_PATHS", "/scan")],
        # Folder names to skip anywhere in the tree (NAS thumbnail/recycle/snapshot dirs).
        exclude_dirs=_list("EXCLUDE_DIRS", "@eaDir,#recycle,#snapshot,.snapshot,@Recycle,.@__thumb,$RECYCLE.BIN"),
        spreadsheet_path=Path(os.environ.get("SPREADSHEET_PATH", "/output/master_invoices.xlsx")),
        state_db_path=Path(os.environ.get("STATE_DB_PATH", "/data/state.db")),
        # Seconds between scans. 0 = run once and exit (use with cron / NAS task scheduler).
        scan_interval=_int("SCAN_INTERVAL_SECONDS", 900),
        # Skip files modified in the last N seconds, so half-copied PDFs aren't read.
        min_file_age=_int("MIN_FILE_AGE_SECONDS", 60),
        # Max PDFs sent to Claude per scan, to cap spend on a first run over a big archive.
        max_files_per_run=_int("MAX_FILES_PER_RUN", 200),
        max_attempts=_int("MAX_ATTEMPTS", 3),
        max_pages=_int("MAX_PAGES", 10),
        ocr_dpi=_int("OCR_DPI", 300),
        ocr_lang=os.environ.get("OCR_LANG", "eng"),
        # A page with fewer embedded-text characters than this gets OCR'd.
        min_text_chars=_int("MIN_TEXT_CHARS", 50),
        model=os.environ.get("CLAUDE_MODEL", "claude-opus-5-5"),
        effort=os.environ.get("CLAUDE_EFFORT", "low"),
        max_text_chars=_int("MAX_TEXT_CHARS", 60000),
    )
