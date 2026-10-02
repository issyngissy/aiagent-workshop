# NAS Invoice Agent 🧾

Watches folders on your NAS, reads every invoice/receipt PDF (OCR for scans), pulls out the key fields with Claude, and appends a row per document to one master Excel file.

## How it works

```
NAS folders ──► scanner ──► text layer? ──yes──► text
 (read-only)      │              │no
                  │              └──► Tesseract OCR ──► text
                  │                                      │
                  │                       Claude (structured output)
                  │                                      │
            state.db (SQLite) ◄──── extracted row ◄──────┘
                  │
                  └──► master_invoices.xlsx (appended, atomic save)
```

- ✅ **Each file once.** Tracked by content hash, so renamed / moved / duplicate PDFs aren't re-sent.
- ✅ **Scans and digital PDFs.** Pages with a text layer skip OCR. Pages without one get OCR'd at 300 DPI.
- ✅ **Excel can be open.** If someone has the sheet open (`~$` lock file), rows queue in `state.db` and get written on the next scan.
- ✅ **Safe saves.** Writes to a temp file then swaps it in, so a crash can't corrupt the master.
- ⚠️ **Needs Review column.** Flagged (and highlighted yellow) when confidence is low, supplier/date/total is missing, or subtotal + tax ≠ total.
- 🔒 **PDFs are mounted read-only.** The agent never edits or moves your files.

## Spreadsheet columns

Processed At, File Name, File Path, Doc Type, Supplier, Supplier ABN, Invoice No., Invoice Date, Due Date, Billed To, Currency, Subtotal, Tax (GST), Total, Description, Confidence, Needs Review, Notes, OCR Pages, File Hash.

To add or change fields: edit `Invoice` in `invoice_agent/extract.py` and `COLUMNS` in `invoice_agent/sheet.py`.

## Setup (any NAS with Docker)

1. Copy this folder onto the NAS, e.g. `/volume1/docker/invoice-agent`.
2. `cp .env.example .env` and set `ANTHROPIC_API_KEY`.
3. Edit the `volumes:` in `docker-compose.yml` so the left side points at your real folders.
4. Set `PUID` / `PGID` in `.env` to your NAS user (run `id` over SSH).
5. Over SSH: `docker compose up -d --build`
6. Watch it: `docker logs -f invoice-agent`

**Synology:** Container Manager ▸ Project ▸ Create ▸ point at the folder. Shares live under `/volume1/<share>`.
**QNAP:** Container Station ▸ Applications ▸ Create, paste the compose file. Shares live under `/share/<share>`.
**No Docker:** install Python 3.11+, Tesseract and `pip install -r requirements.txt`, set the env vars, then run `python -m invoice_agent.main` from the NAS task scheduler with `SCAN_INTERVAL_SECONDS=0`.

## First run on a big archive 💸

`MAX_FILES_PER_RUN` (default 200) caps how many PDFs go to Claude per scan. Start small, check the sheet, then raise it.

## Config

| Variable | Default | What it does |
|---|---|---|
| `SCAN_PATHS` | `/scan` | Comma-separated folders to scan (recursive) |
| `SPREADSHEET_PATH` | `/output/master_invoices.xlsx` | Master spreadsheet |
| `STATE_DB_PATH` | `/data/state.db` | Processing record. Delete it to reprocess everything |
| `SCAN_INTERVAL_SECONDS` | `900` | Time between scans. `0` = run once and exit |
| `MIN_FILE_AGE_SECONDS` | `60` | Skip files still being copied in |
| `MAX_FILES_PER_RUN` | `200` | Spend cap per scan |
| `MAX_ATTEMPTS` | `3` | Retries for a failing file before giving up |
| `MAX_PAGES` | `10` | Pages read per PDF |
| `OCR_LANG` | `eng` | Tesseract language(s), e.g. `eng+chi_sim` (add the pack in the Dockerfile) |
| `CLAUDE_MODEL` | `claude-opus-5-5` | Model used for extraction |
| `CLAUDE_EFFORT` | `low` | Reasoning effort. Raise to `medium` if messy scans come out wrong |
| `EXCLUDE_DIRS` | NAS system dirs | Folder names to skip (`@eaDir`, `#recycle`, ...) |

## Privacy

OCR runs on the NAS. The **extracted text** (not the PDF) is sent to the Anthropic API for field extraction.

## Tests

```bash
pip install -r requirements.txt pytest   # also needs the tesseract binary
pytest -q
```

Tests use a fake extractor, so they don't call the API or need a key.
