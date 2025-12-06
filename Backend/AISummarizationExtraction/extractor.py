from typing import Optional

def extract_text_from_pdf_bytes(data: bytes) -> str:
    try:
        from pypdf import PdfReader
        from io import BytesIO

        reader = PdfReader(BytesIO(data))
        texts = []
        for page in reader.pages:
            texts.append(page.extract_text() or "")
        return "\n".join(texts)
    except Exception:
        return ""


def extract_text_from_docx_bytes(data: bytes) -> str:
    try:
        from docx import Document as DocxDocument
        from io import BytesIO

        doc = DocxDocument(BytesIO(data))
        paragraphs = [p.text for p in doc.paragraphs]
        return "\n".join(paragraphs)
    except Exception:
        return ""


def extract_text(filename: str, data: bytes) -> str:
    fname = filename.lower()
    if fname.endswith(".pdf"):
        return extract_text_from_pdf_bytes(data)
    if fname.endswith(".docx") or fname.endswith(".doc"):
        return extract_text_from_docx_bytes(data)
    try:
        return data.decode("utf-8")
    except Exception:
        return ""
