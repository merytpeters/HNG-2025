from datetime import datetime, timezone
from typing import Optional, Dict
import uuid

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON, ForeignKey
from sqlalchemy import Text as SQLText
from sqlalchemy.dialects.mysql import CHAR, LONGTEXT


def new_uuid() -> str:
    return str(uuid.uuid4())


class Document(SQLModel, table=True):
    id: Optional[str] = Field(
        default_factory=new_uuid, sa_column=Column(CHAR(36), primary_key=True)
    )
    filename: str
    content_type: Optional[str] = None
    size: Optional[int] = None
    storage_path: Optional[str] = None
    storage_type: Optional[str] = None
    content_text: Optional[str] = Field(default=None, sa_column=Column(LONGTEXT))
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentAnalysis(SQLModel, table=True):
    id: Optional[str] = Field(
        default_factory=new_uuid, sa_column=Column(CHAR(36), primary_key=True)
    )
    document_id: str = Field(sa_column=Column(CHAR(36), ForeignKey("document.id")))

    summary: Optional[str] = Field(default=None, sa_column=Column(LONGTEXT))
    doc_type: Optional[str] = None
    attributes: Optional[Dict] = Field(sa_column=Column(JSON), default_factory=dict)
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
