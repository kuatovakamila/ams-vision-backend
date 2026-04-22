import logging
import io
from typing import Optional, Tuple
from datetime import timedelta
from minio import Minio
from minio.error import S3Error
from fastapi import HTTPException, status, UploadFile

from .config import settings

logger = logging.getLogger(__name__)


class MinIOClient:
    """MinIO client for handling file operations"""

    def __init__(self):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
            region=settings.minio_region,
        )
        self.bucket_name = settings.minio_bucket
        self.folder_prefix = settings.minio_folder_prefix

        # Ensure bucket exists
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(
                    self.bucket_name, location=settings.minio_region
                )
                logger.info(f"Created MinIO bucket: {self.bucket_name}")
            else:
                logger.info(f"MinIO bucket exists: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Error checking/creating bucket: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"MinIO bucket error: {str(e)}",
            )

    def _get_object_name(self, filename: str, folder_path: str = None) -> str:
        """Get the full object name including folder prefix and folder path"""
        parts = []

        # Add base folder prefix
        if self.folder_prefix:
            parts.append(self.folder_prefix)

        # Add folder path if provided
        if folder_path:
            # Remove leading/trailing slashes and split
            folder_path = folder_path.strip("/")
            if folder_path:
                parts.append(folder_path)

        # Add filename
        parts.append(filename)

        return "/".join(parts)

    async def upload_file(
        self, upload_file: UploadFile, filename: str, folder_path: str = None
    ) -> Tuple[str, int]:
        """
        Upload file to MinIO
        Returns: (object_name, file_size)
        """
        try:
            # Read file content
            content = await upload_file.read()
            file_size = len(content)

            # Reset file pointer for potential re-reading
            await upload_file.seek(0)

            object_name = self._get_object_name(filename, folder_path)

            # Upload to MinIO
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=io.BytesIO(content),
                length=file_size,
                content_type=upload_file.content_type or "application/octet-stream",
            )

            logger.info(
                f"File uploaded to MinIO: {object_name}, size: {file_size} bytes"
            )
            return object_name, file_size

        except S3Error as e:
            logger.error(f"MinIO upload error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file to MinIO: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Upload error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file: {str(e)}",
            )

    def get_presigned_download_url(
        self, object_name: str, filename: Optional[str] = None
    ) -> str:
        """
        Get a presigned URL for downloading a file
        """
        try:
            # Prepare response headers for download
            response_headers = {}
            if filename:
                response_headers["response-content-disposition"] = (
                    f'attachment; filename="{filename}"'
                )

            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=timedelta(seconds=settings.minio_presigned_url_expiry),
                response_headers=response_headers if response_headers else None,
            )

            logger.info(f"Generated presigned URL for: {object_name}")
            return url

        except S3Error as e:
            logger.error(f"MinIO presigned URL error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate download URL: {str(e)}",
            )

    def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from MinIO
        Returns: True if successful, False if file doesn't exist
        """
        try:
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"File deleted from MinIO: {object_name}")
            return True

        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.warning(f"File not found in MinIO: {object_name}")
                return False
            logger.error(f"MinIO delete error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete file from MinIO: {str(e)}",
            )

    def file_exists(self, object_name: str) -> bool:
        """
        Check if a file exists in MinIO
        """
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            logger.error(f"MinIO stat error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to check file existence: {str(e)}",
            )

    def get_file_info(self, object_name: str) -> dict:
        """
        Get file information from MinIO
        """
        try:
            stat = self.client.stat_object(self.bucket_name, object_name)
            return {
                "size": stat.size,
                "etag": stat.etag,
                "last_modified": stat.last_modified,
                "content_type": stat.content_type,
            }
        except S3Error as e:
            if e.code == "NoSuchKey":
                return None
            logger.error(f"MinIO stat error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get file info: {str(e)}",
            )


# Global MinIO client instance
minio_client = MinIOClient()
