from datetime import timedelta
from typing import Optional

from google.cloud.storage import Client

from .client import StorageClient
from .config import config
from .exception import StorageException
from .http import HttpMethod
from .log import logger


class GCS(StorageClient):
    """
    GCS.
    """

    _gcs_client = None
    _gcs_project = None
    _use_public_urls = None

    @classmethod
    def _project(cls):
        if cls._gcs_project is None:
            raise StorageException(
                "gcs client requires that the GOOGLE_CLOUD_PROJECT env"
                " variable is present"
            )
        return cls._gcs_project

    @classmethod
    def _client(cls):
        if cls._gcs_client is None:
            raise StorageException("gcs client has not been configured")
        return cls._gcs_client

    @classmethod
    def configure(cls) -> None:
        gcs_config = {
            key: value
            for key, value in config().items()
            if key
            in (
                "STORAGE_EMULATOR_HOST",
                "GOOGLE_CLOUD_PROJECT",
            )
        }
        cls._gcs_project = gcs_config["GOOGLE_CLOUD_PROJECT"]

        if gcs_config["STORAGE_EMULATOR_HOST"] is not None:
            logger.debug(
                "will not sign urls due to presense of %s",
                "STORAGE_EMULATOR_HOST",
            )
            # we won't actually sign urls in this case
            cls._use_public_urls = True

        cls._gcs_client = Client(project=cls._gcs_project)

    def bucket_exists(self, name: str) -> bool:
        bucket = self._client().bucket(name)
        return bucket.exists()

    def make_bucket(self, name: str) -> None:
        if self.bucket_exists(name):
            raise StorageException("bucket {0} already exists".format(name))
        self._client().create_bucket(name)

    def remove_bucket(self, name: str) -> None:
        self._client().bucket(name).delete()

    def delete_object(self, bucket_name: str) -> None:
        if not self.bucket_exists(bucket_name):
            raise StorageException(
                "bucket {0} does not exist".format(bucket_name)
            )

    def put_object(
        self,
        bucket_name: str,
        name: str,
        data: object,
        size: int,
        content_type: str,
    ) -> None:
        raise StorageException("put is not yet implemented")

    def object_exists(self, bucket_name: str, name: str) -> bool:
        if not self.bucket_exists(bucket_name):
            raise StorageException(
                "bucket {0} does not exist".format(bucket_name)
            )
        return False

    def get_presigned_url(
        self,
        bucket_name: str,
        name: str,
        method: HttpMethod,
        expires: Optional[timedelta],
        content_type: Optional[str] = None,
    ) -> str:
        if not self.bucket_exists(bucket_name):
            raise StorageException(
                "bucket {0} does not exist".format(bucket_name)
            )
        bucket = self._client().get_bucket(bucket_name)
        blob = bucket.blob(name)
        return (
            blob.generate_signed_url(
                expiration=expires, method=method, content_type=content_type
            )
            if not GCS._use_public_urls
            else blob.public_url
        )
