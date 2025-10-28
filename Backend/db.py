"""Base SQL Engine"""

from pathlib import Path
from dotenv import load_dotenv
from sqlmodel import create_engine, Session
import os


env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL is not set.")

engine = create_engine(DATABASE_URL, echo=True)


def get_session():
    """Database session."""
    with Session(engine) as session:
        yield session
