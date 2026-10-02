"""SQLite record of which files have been processed, so each scan only handles new PDFs.

Extracted rows are stored here first and flushed to the spreadsheet separately. If the
spreadsheet is open in Excel (locked), nothing is lost: rows wait here until the next scan.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    sha256        TEXT PRIMARY KEY,
    path          TEXT NOT NULL,
    status        TEXT NOT NULL,          -- extracted | written | error
    attempts      INTEGER NOT NULL DEFAULT 0,
    error         TEXT,
    row_json      TEXT,
    updated_at    TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class State:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(SCHEMA)
        self.conn.commit()

    def should_process(self, sha256: str, max_attempts: int) -> bool:
        row = self.conn.execute("SELECT status, attempts FROM files WHERE sha256 = ?", (sha256,)).fetchone()
        if row is None:
            return True
        status, attempts = row
        return status == "error" and attempts < max_attempts

    def mark_extracted(self, sha256: str, path: Path, row: dict) -> None:
        self.conn.execute(
            """INSERT INTO files (sha256, path, status, attempts, error, row_json, updated_at)
               VALUES (?, ?, 'extracted', 1, NULL, ?, ?)
               ON CONFLICT(sha256) DO UPDATE SET path=excluded.path, status='extracted',
                   attempts=files.attempts + 1, error=NULL, row_json=excluded.row_json, updated_at=excluded.updated_at""",
            (sha256, str(path), json.dumps(row), _now()),
        )
        self.conn.commit()

    def mark_error(self, sha256: str, path: Path, error: str) -> None:
        self.conn.execute(
            """INSERT INTO files (sha256, path, status, attempts, error, updated_at)
               VALUES (?, ?, 'error', 1, ?, ?)
               ON CONFLICT(sha256) DO UPDATE SET path=excluded.path, status='error',
                   attempts=files.attempts + 1, error=excluded.error, updated_at=excluded.updated_at""",
            (sha256, str(path), error[:2000], _now()),
        )
        self.conn.commit()

    def pending_rows(self) -> list[tuple[str, dict]]:
        rows = self.conn.execute("SELECT sha256, row_json FROM files WHERE status = 'extracted' ORDER BY updated_at")
        return [(sha, json.loads(js)) for sha, js in rows]

    def mark_written(self, hashes: list[str]) -> None:
        self.conn.executemany(
            "UPDATE files SET status='written', updated_at=? WHERE sha256=?", [(_now(), h) for h in hashes]
        )
        self.conn.commit()

    def errors(self) -> list[tuple[str, str, int]]:
        return self.conn.execute("SELECT path, error, attempts FROM files WHERE status='error'").fetchall()
