"""MinIO client and object-storage operations will be added in the next step."""
import os
import tempfile
import uuid
from datetime import timedelta
from io import BytesIO

from minio import Minio
from minio.error import S3Error
from app.database import settings


def _build_minio_client(endpoint: str) -> Minio:
    access_key = settings.minio_access_key
    secret_key = settings.minio_secret_key


    secure = endpoint.startswith("https://")
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        endpoint = endpoint.split("://", 1)[1]

    return Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
        # Pin the region so the client never issues a GetBucketLocation
        # request against `endpoint` to resolve it (that request would fail
        # for a browser-facing endpoint that isn't reachable from this
        # container, e.g. minio_public_endpoint pointing at a host port).
        region="us-east-1",
    )


def get_minio_client() -> Minio:
    return _build_minio_client(settings.minio_endpoint)


def ensure_bucket_exists(bucket_name: str) -> None:
    client = get_minio_client()
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)


def upload_file_to_minio(file_content: bytes, file_name: str, content_type: str = "application/pdf") -> str:
    bucket_name = settings.minio_bucket_name
    ensure_bucket_exists(bucket_name)
    client = get_minio_client()
    object_name = f"{uuid.uuid4()}_{file_name}"
    client.put_object(
        bucket_name,
        object_name,
        BytesIO(file_content),
        length=len(file_content),
        content_type=content_type,
    )
    return object_name


def upload_bytes_to_minio(file_content: bytes, object_name: str, content_type: str = "application/pdf") -> str:
    bucket_name = settings.minio_bucket_name
    ensure_bucket_exists(bucket_name)
    client = get_minio_client()
    client.put_object(
        bucket_name,
        object_name,
        BytesIO(file_content),
        length=len(file_content),
        content_type=content_type,
    )
    return object_name


def get_presigned_get_url(object_name: str, expires_seconds: int = 3600) -> str:
    bucket_name = settings.minio_bucket_name
    client = get_minio_client()
    return client.presigned_get_object(
        bucket_name,
        object_name,
        expires=timedelta(seconds=expires_seconds),
    )

def upload_media_to_minio(file_content: bytes, file_name: str, content_type: str) -> str:
    bucket_name = settings.minio_bucket_name
    ensure_bucket_exists(bucket_name)
    client = get_minio_client()
    object_name = f"message_media/{uuid.uuid4()}_{file_name}"
    client.put_object(
        bucket_name=bucket_name,
        object_name=object_name,
        data=BytesIO(file_content),
        length=len(file_content),
        content_type=content_type,
    )
    return object_name


def get_file_bytes_from_minio(object_name: str) -> bytes:
    bucket_name = settings.minio_bucket_name
    client = get_minio_client()
    response =None
    try:
        response = client.get_object(
            bucket_name=bucket_name,
            object_name=object_name )
        return response.read()

    finally:
        if response is not None:
           response.close()
           response.release_conn()



__all__ = [
    "upload_file_to_minio",
    "upload_bytes_to_minio",
    "get_presigned_get_url",
    "get_minio_client",
    "ensure_bucket_exists",
    "upload_media_to_minio",
    "get_file_bytes_from_minio",
]
