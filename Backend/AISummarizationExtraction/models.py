from datetime import datetime, timezone
from typing import Optional, Dict

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON


class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    content_type: Optional[str] = None
    size: Optional[int] = None
    storage_path: Optional[str] = None
    storage_type: Optional[str] = None
    content_text: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentAnalysis(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="document.id")
    summary: Optional[str] = None
    doc_type: Optional[str] = None
    attributes: Optional[Dict] = Field(sa_column=Column(JSON), default={})
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
