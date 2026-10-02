FROM python:3.12-slim

# Tesseract does the OCR. Add more language packs here if needed (e.g. tesseract-ocr-chi-sim).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY invoice_agent ./invoice_agent

ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "invoice_agent.main"]
