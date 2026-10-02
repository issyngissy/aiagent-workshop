"""Get text out of a PDF: use the embedded text layer when it exists, OCR the page when it doesn't."""

import io
import logging
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

log = logging.getLogger(__name__)


@dataclass
class PdfText:
    text: str
    page_count: int
    pages_read: int
    ocr_pages: int


def extract_text(path: Path, max_pages: int, dpi: int, lang: str, min_text_chars: int) -> PdfText:
    parts: list[str] = []
    ocr_pages = 0
    with fitz.open(path) as doc:
        pages_read = min(doc.page_count, max_pages)
        for i in range(pages_read):
            page = doc.load_page(i)
            text = page.get_text("text").strip()
            if len(text) < min_text_chars:
                # Scanned page (no usable text layer): render to an image and OCR it.
                pix = page.get_pixmap(dpi=dpi)
                image = Image.open(io.BytesIO(pix.tobytes("png")))
                text = pytesseract.image_to_string(image, lang=lang).strip()
                ocr_pages += 1
            parts.append(f"--- Page {i + 1} ---\n{text}")
        page_count = doc.page_count
    if page_count > pages_read:
        log.info("%s has %d pages, only read the first %d", path, page_count, pages_read)
    return PdfText(text="\n\n".join(parts), page_count=page_count, pages_read=pages_read, ocr_pages=ocr_pages)
