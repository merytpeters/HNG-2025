from datetime import datetime, timezone
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from db import get_session
from .models import Document, DocumentAnalysis
from .storage import save_file_bytes
from .extractor import extract_text
from .openrouter import analyze_text


app = FastAPI(title="AISummarizationExtraction Subapp")


@app.post("/upload")
def upload_document(file: UploadFile = File(...), db: Session = Depends(get_session)):
    """Upload a PDF or DOCX (max 5MB), save file, extract text and store metadata."""
    contents = file.file.read()
    size = len(contents)
    max_size = 5 * 1024 * 1024
    if size > max_size:
        raise HTTPException(status_code=413, detail="File too large (max 5MB)")

    filename = file.filename
    if filename is None:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename")
    storage_type, storage_path = save_file_bytes(filename, contents)

    text = extract_text(filename, contents)

    doc = Document(
        filename=filename,
        content_type=file.content_type,
        size=size,
        storage_path=storage_path,
        storage_type=storage_type,
        content_text=text,
        uploaded_at=datetime.now(timezone.utc),
    )

    db.add(doc)
    db.commit()
    db.refresh(doc)

    return JSONResponse({"id": doc.id, "filename": doc.filename, "storage": doc.storage_path})


@app.post("/{doc_id}/analyze")
def analyze_document(doc_id: int, db: Session = Depends(get_session)):
    """Send extracted text to LLM and save response."""
    doc = db.exec(select(Document).where(Document.id == doc_id)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if not doc.content_text:
        raise HTTPException(status_code=400, detail="No extracted text available for document")

    result = analyze_text(doc.content_text)

    if doc.id is None:
        raise HTTPException(status_code=500, detail="Document id missing after commit")

    analysis = DocumentAnalysis(
        document_id=int(doc.id),
        summary=result.get("summary"),
        doc_type=result.get("doc_type"),
        attributes=result.get("attributes") or {},
        analyzed_at=datetime.now(timezone.utc),
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return analysis


@app.get("/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_session)):
    doc = db.exec(select(Document).where(Document.id == doc_id)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    analysis = (
        db.exec(
            select(DocumentAnalysis).where(DocumentAnalysis.document_id == doc_id).order_by(DocumentAnalysis.analyzed_at.desc())
        )
        .first()
    )

    return {
        "file": {
            "id": doc.id,
            "filename": doc.filename,
            "content_type": doc.content_type,
            "size": doc.size,
            "storage_type": doc.storage_type,
            "storage_path": doc.storage_path,
            "uploaded_at": doc.uploaded_at,
        },
        "text": doc.content_text,
        "analysis": analysis,
    }
