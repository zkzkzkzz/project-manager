import boto3
from botocore.client import Config
import os
from botocore.exceptions import ClientError
from fastapi import UploadFile, HTTPException
import logging


import uuid

from typing_extensions import Optional

from .settings import settings

logger = logging.getLogger(__name__)

S3_INTERNAL_ENDPOINT = settings.AWS_S3_ENDPOINT_URL
S3_PUBLIC_ENDPOINT = os.getenv("PUBLIC_S3_HOST")
BUCKET = settings.S3_BUCKET_NAME

AWS_ACCESS_KEY = settings.AWS_ACCESS_KEY_ID
AWS_SECRET_KEY = settings.AWS_SECRET_ACCESS_KEY
AWS_REGION = settings.AWS_REGION

if not all([S3_INTERNAL_ENDPOINT, BUCKET, AWS_ACCESS_KEY, AWS_SECRET_KEY]):

    raise RuntimeError("Missing critical S3 configuration environment variables.")
if not S3_PUBLIC_ENDPOINT:
    print(
        "Warning: PUBLIC_S3_HOST is not set. Presigned URLs for browser might not use public host."
    )


boto_client_kwargs = {
    "endpoint_url": S3_INTERNAL_ENDPOINT,
    "aws_access_key_id": AWS_ACCESS_KEY,
    "aws_secret_access_key": AWS_SECRET_KEY,
    # --- ADD S3 CONFIGURATION FOR PATH STYLE ---
    "config": Config(s3={"addressing_style": "path", "signature_version": "s3v4"}),
    # Explicitly setting signature_version to s3v4 is also good practice with MinIO
}


try:
    s3_client = boto3.client("s3", **boto_client_kwargs)
    logger.info(
        f"S3_UTILS: Boto3 S3 client initialized for endpoint: {S3_INTERNAL_ENDPOINT} with path-style addressing."
    )
except Exception as e:
    logger.critical(
        f"S3_UTILS: FATAL - Could not create boto3 S3 client. Error: {e}", exc_info=True
    )
    s3_client = None


class S3Store:
    def __init__(self):
        self.client = s3_client
        self.bucket = BUCKET
        self.internal = S3_INTERNAL_ENDPOINT
        self.public = S3_PUBLIC_ENDPOINT or S3_INTERNAL_ENDPOINT

    @staticmethod
    def make_key(project_id: int, filename: str) -> str:
        """generate a unique S3 key for a file"""
        uid = uuid.uuid4()

        return f"projects/{project_id}/uploads/{uid}_{filename}"

    def upload(self, file: UploadFile, project_id: int) -> str:
        """upload and return the S3 key"""
        name = file.filename or "unnamed"
        key = self.make_key(project_id, name)

        try:
            self.client.upload_fileobj(
                file.file,
                self.bucket,
                key,
                ExtraArgs={"ContentType": file.content_type},
            )
            return key
        except ClientError as ce:
            msg = ce.response.get("Error", {}).get("Message", str(ce))
            raise HTTPException(500, f"S3 upload failed: {msg}")

    def delete(self, key: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            print(f"S3_STORE: Successfully deleted {key}...")
            return True
        except ClientError as ce:
            print(f"[S3 Delete Error] key={key}: {ce}")
            return False

    def presign(self, key: str, expires: int = 3600) -> Optional[str]:
        try:
            internal_url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires,
            )
            public_url = internal_url.replace(self.internal, self.public)
            return public_url

        except ClientError as ce:
            print(f"[S3 Presign Error] key={key}: {ce}")
            return None


s3_store = S3Store()
