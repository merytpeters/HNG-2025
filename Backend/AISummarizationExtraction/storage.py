import os
from pathlib import Path
from typing import Tuple
from dotenv import load_dotenv
import logging
import io
import uuid
import mimetypes
from urllib.parse import urlparse
from datetime import datetime, timezone

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() in ("1", "true", "yes")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "documents")

logger = logging.getLogger(__name__)


def _normalize_endpoint(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    return parsed.netloc or parsed.path


def save_file_bytes(filename: str, data: bytes) -> Tuple[str, str]:
    """
    Save file to MinIO if configured, else save locally.
    Returns (storage_type, storage_path)
    """
    if MINIO_ENDPOINT and MINIO_ACCESS_KEY and MINIO_SECRET_KEY:
        try:
            from minio import Minio

            endpoint = _normalize_endpoint(MINIO_ENDPOINT)
            client = Minio(
                endpoint,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_SECURE,
            )

            if not client.bucket_exists(MINIO_BUCKET):
                client.make_bucket(MINIO_BUCKET)

            safe_name = Path(filename).name
            key = f"documents/{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/{uuid.uuid4().hex}-{safe_name}"

            stream = io.BytesIO(data)
            content_type = (
                mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
            )
            client.put_object(
                MINIO_BUCKET, key, stream, length=len(data), content_type=content_type
            )

            path = f"minio://{MINIO_BUCKET}/{key}"
            return ("minio", path)

        except Exception as e:
            logger.error(f"MinIO upload failed: {e}")
            raise

    base = Path(__file__).parent.parent
    storage_dir = base / "storage" / "documents"
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_path = storage_dir / filename
    with open(file_path, "wb") as f:
        f.write(data)

    return ("local", str(file_path))
