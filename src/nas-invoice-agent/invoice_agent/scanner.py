"""Walk the configured folders and yield PDFs that are ready to process."""

import hashlib
import logging
import os
import time
from pathlib import Path
from typing import Iterator

log = logging.getLogger(__name__)


def find_pdfs(roots: list[Path], exclude_dirs: list[str], min_age_seconds: int) -> Iterator[Path]:
    excluded = set(exclude_dirs)
    cutoff = time.time() - min_age_seconds
    for root in roots:
        if not root.is_dir():
            log.warning("Scan path does not exist or is not a folder: %s", root)
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            # Prune in place so os.walk never descends into excluded dirs.
            dirnames[:] = [d for d in dirnames if d not in excluded and not d.startswith(".")]
            for name in filenames:
                if not name.lower().endswith(".pdf") or name.startswith("."):
                    continue
                path = Path(dirpath) / name
                try:
                    if path.stat().st_mtime > cutoff:
                        log.debug("Skipping recently modified file: %s", path)
                        continue
                except OSError:
                    continue
                yield path


def file_hash(path: Path) -> str:
    """Content hash, so renamed or moved files aren't processed twice."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
