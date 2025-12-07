import os
from pathlib import Path
from typing import Tuple
from dotenv import load_dotenv
import logging

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() in ("1", "true", "yes")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "documents")

logger = logging.getLogger(__name__)


def save_file_bytes(filename: str, data: bytes) -> Tuple[str, str]:
    """
    Save file to MinIO if configured, else save locally.
    Returns (storage_type, storage_path)
    """
    if MINIO_ENDPOINT and MINIO_ACCESS_KEY and MINIO_SECRET_KEY:
        try:
            from minio import Minio
            from minio.error import S3Error

            client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_SECURE,
            )

            if not client.bucket_exists(MINIO_BUCKET):
                client.make_bucket(MINIO_BUCKET)

            client.put_object(MINIO_BUCKET, filename, data, length=len(data))
            path = f"minio://{MINIO_BUCKET}/{filename}"
            return ("minio", path)

        except Exception as e:
            logger.warning(f"MinIO upload failed: {e}. Falling back to local storage.")

    base = Path(__file__).parent.parent
    storage_dir = base / "storage" / "documents"
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_path = storage_dir / filename
    with open(file_path, "wb") as f:
        f.write(data)

    return ("local", str(file_path))
