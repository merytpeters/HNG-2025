# AISummarizationExtraction (Task 7)

AI Document Summarization + Metadata Extraction Workflow

## Overview
This service accepts PDF or DOCX documents, extracts text and basic metadata, sends the extracted text to an LLM via OpenRouter, and returns:
- Concise summary
- Detected document type (invoice, CV, report, letter, etc.)
- Extracted attributes/metadata (date, sender, total amount, etc.)

Core endpoints:
- POST /upload — accept PDF (max 5 MB) or DOCX, store raw file in S3/Minio, extract text & save to DB.
- POST /{doc_id}/analyze — send stored text to an LLM (OpenRouter), save summary/type/attributes to DB.
- GET /{doc_id} — return combined data: file info, extracted text, LLM outputs.

## High-level flow
1. Client uploads file → validate (PDF/DOCX, <=5MB).
2. Store file in object storage (S3/Minio) and create DB record (document id, S3 key, original filename, upload timestamp).
3. Extract text and light metadata (use pdf parsing + docx parser; run heuristics/regex for dates/amounts).
4. Save text and metadata to DB.
5. On analyze call, send text to OpenRouter LLM (e.g., gpt-4o-mini or other model), requesting:
   - concise summary
   - document type classification
   - structured metadata (date, sender, total amount, etc.)
6. Save LLM outputs in DB and return via GET endpoint.

## API

### POST /upload
- Accepts: multipart/form-data with `file` (PDF or DOCX)
- Constraints: max 5 MB
- Actions:
  - Validate file type & size
  - Upload raw file to S3/Minio
  - Extract text & basic metadata
  - Persist entry in DB
- Response (201):
  {
    "id": "<uuid>",
    "filename": "invoice.pdf",
    "storage": "documents/2025/03/<uuid>-invoice.pdf"
  }

### POST /{doc_id}/analyze
- Body: optional params (model, temperature)
- Actions:
  - Load extracted text from DB
  - Build prompt(s) to request summary, type, attributes
  - Call OpenRouter (model e.g., gpt-4o-mini) using your OPENROUTER_API_KEY
  - Validate & normalize LLM response into structured JSON
  - Save summary/type/attributes to DB
- Response (200):
  The endpoint returns the saved DocumentAnalysis object with fields:
  {
    "id": "<analysis-id>",
    "document_id": "<document-id>",
    "summary": "Short concise summary...",
    "doc_type": "invoice",            // note field name doc_type per app.py
    "attributes": {
      "date": "2025-03-01",
      "sender": "ACME Corp",
      "total_amount": "1234.56",
      ...
    },
    "analyzed_at": "2025-03-05T12:34:56.789Z"
  }

### GET /{doc_id}
- Returns combined document record matching app.py's output:
  {
    "file": {
      "id": "<document-id>",
      "filename": "invoice.pdf",
      "content_type": "application/pdf",
      "size": 12345,
      "storage_type": "s3" | "minio" | ...,
      "storage_path": "documents/2025/03/<uuid>-invoice.pdf",
      "uploaded_at": "2025-03-05T11:22:33.444Z"
    },
    "text": "Full extracted text of the document ...",
    "analysis": {
      "id": "<analysis-id>",
      "document_id": "<document-id>",
      "summary": "Short concise summary...",
      "doc_type": "invoice",
      "attributes": {
        "date": "2025-03-01",
        "sender": "ACME Corp",
        "total_amount": "1234.56",
        ...
      },
      "analyzed_at": "2025-03-05T12:34:56.789Z"
    }  // analysis may be null if no analysis exists
  }

## Implementation notes
- File handling
  - Enforce 5MB limit server-side and in reverse proxy.
  - Accept MIME types: `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`.
- Storage
  - Use Minio for local development or AWS S3 in production.
  - Key pattern: documents/{year}/{month}/{uuid}-{sanitized-filename}
- Text extraction
  - PDF: pdf-parse, PyPDF2, or pdfplumber (Node: pdf-parse or pdfjs)
  - DOCX: mammoth (Node) or python-docx
  - Normalize newlines & strip excessive whitespace.
- Initial metadata extraction
  - Use simple regexes to find dates, currency amounts, emails, phone numbers.
  - Save these as `raw_metadata` before LLM enrichment.
- LLM (OpenRouter)
  - Use OpenRouter to proxy to models. Supply OPENROUTER_API_KEY as env var.
  - Prompt template: ask for JSON with fields {summary, type, attributes} and strict JSON output.
  - Consider chunking long documents and either summarize per-chunk then combine, or send full text if within model limits.
  - Validate JSON and sanitize numeric/date fields before persisting.

## Suggested DB schema (relational or document)
documents table/collection:
- id (uuid)
- filename
- uploaded_at
- raw_metadata (json)
- extracted_text (text)
- analysis (json): { summary, type, attributes, analyzed_at }

## Prompt example (pseudo)
"You are a document analyzer. Given the text delimited by triple backticks, return a JSON object with keys: summary (one paragraph), type (one of invoice, cv, report, letter, other), attributes (object with keys: date, sender, recipient, total_amount, currency, invoice_number — use null if not found). Respond only with JSON."

## Security & reliability
- Validate file types and scan for malware if possible.
- Require authentication/authorization for upload/analyze endpoints.
- Rate-limit analyze endpoint to control LLM costs.
- Log request IDs, errors, and OpenRouter usage.
- Sanitize and validate LLM outputs before saving.

## Troubleshooting & tips
- If LLM returns non-JSON, re-prompt with stricter instructions or add a JSON extraction layer.
- For long documents, summarize in chunks and then ask the LLM to merge chunk summaries.
- Keep a copy of raw LLM output for auditing.


Contributions, issues and improvements can be tracked in the repo. Keep OpenRouter keys and storage credentials out of source control.
