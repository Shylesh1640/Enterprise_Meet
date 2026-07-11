"""Enterprise Meet — MinIO storage utilities."""

from __future__ import annotations

import io
import uuid
from typing import Tuple

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _get_minio_client():
    """Return a configured MinIO client."""
    from minio import Minio

    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def ensure_bucket_exists(bucket_name: str) -> None:
    """Create bucket if it doesn't already exist."""
    client = _get_minio_client()
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
        logger.info("bucket_created", bucket=bucket_name)


async def upload_to_minio(
    content: bytes,
    filename: str,
    content_type: str,
    bucket: str,
    prefix: str = "",
) -> Tuple[str, str]:
    """
    Upload bytes to MinIO.
    Returns (object_key, presigned_url).
    """
    import asyncio

    # Generate unique key
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    unique_name = f"{uuid.uuid4().hex}.{ext}" if ext else str(uuid.uuid4().hex)
    object_key = f"{prefix.strip('/')}/{unique_name}".lstrip("/")

    def _upload():
        client = _get_minio_client()
        ensure_bucket_exists(bucket)
        client.put_object(
            bucket,
            object_key,
            io.BytesIO(content),
            length=len(content),
            content_type=content_type,
        )
        # Generate 7-day presigned URL
        from datetime import timedelta
        url = client.presigned_get_object(bucket, object_key, expires=timedelta(days=7))
        return url

    # Run blocking MinIO call in thread pool
    url = await asyncio.get_event_loop().run_in_executor(None, _upload)
    logger.info("file_uploaded_to_minio", key=object_key, size=len(content))
    return object_key, url


def get_presigned_url(bucket: str, object_key: str, expires_hours: int = 1) -> str:
    """Generate a presigned download URL."""
    from datetime import timedelta

    client = _get_minio_client()
    return client.presigned_get_object(
        bucket, object_key, expires=timedelta(hours=expires_hours)
    )
