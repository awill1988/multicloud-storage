from base64 import b64decode
from binascii import hexlify
from datetime import timedelta
from io import BytesIO
from typing import Optional, Union

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

    _gcs_client: Client = None
    _gcs_project = None
    _use_public_urls: Optional[bool] = None
    _emulator_hostname: Optional[str] = None
    _external_hostname: Optional[str] = None
    _secure: bool = True

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
                "STORAGE_EXTERNAL_HOSTNAME",
            )
        }
        cls._gcs_project = gcs_config["GOOGLE_CLOUD_PROJECT"]
        cls._emulator_hostname = gcs_config["STORAGE_EMULATOR_HOST"]

        cls._external_hostname = (
            gcs_config["STORAGE_EXTERNAL_HOSTNAME"]
            if gcs_config["STORAGE_EXTERNAL_HOSTNAME"] is not None
            else cls._emulator_hostname
        )

        if cls._emulator_hostname is not None:
            if cls._emulator_hostname.find("https") == -1:
                cls._secure = False

            logger.debug(
                "will not sign urls due to presense of %s",
                "STORAGE_EMULATOR_HOST",
            )
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
        if not self.bucket_exists(name):
            raise StorageException("bucket {0} does not exist".format(name))
        bucket = self._client().bucket(name)
        bucket.delete()

    def delete_object(self, bucket_name: str, name: str) -> None:
        if not self.bucket_exists(bucket_name):
            raise StorageException(
                "bucket {0} does not exist".format(bucket_name)
            )
        self._client().bucket(bucket_name).blob(name).delete()

    def put_object(
        self,
        bucket_name: str,
        name: str,
        data: BytesIO,
        _: int = 0,
    ) -> None:
        blob = self._client().bucket(bucket_name).blob(name)
        with blob.open("wb") as outfile:
            outfile.write(data.getbuffer())

    def object_exists(self, bucket_name: str, name: str) -> bool:
        if not self.bucket_exists(bucket_name):
            raise StorageException(
                "bucket {0} does not exist".format(bucket_name)
            )
        return self._client().bucket(bucket_name).blob(name).exists()

    def get_object(self, bucket_name: str, name: str) -> BytesIO:
        if not self.object_exists(bucket_name, name):
            raise StorageException(
                "object {0} does not exist in bucket {1}".format(
                    name, bucket_name
                )
            )
        bucket = self._client().bucket(bucket_name)
        blob = bucket.blob(name)
        return BytesIO(blob.download_as_bytes())

    def get_presigned_url(  # pylint: disable=keyword-arg-before-vararg
        self,
        bucket_name: str,
        name: str,
        method: Union[str, HttpMethod],
        expires: Optional[timedelta],
        content_type: Optional[str] = None,
        *_,
    ) -> str:
        if not self.bucket_exists(bucket_name):
            raise StorageException(
                "bucket {0} does not exist".format(bucket_name)
            )
        bucket = self._client().get_bucket(bucket_name)
        blob = bucket.blob(name)
        _method = (method.value if not isinstance(method, str) else method,)
        if not blob.exists() and _method == "GET":
            raise StorageException(
                "object {0} does not exist in bucket {1}".format(
                    name, bucket_name
                )
            )
        if self._use_public_urls:
            _scheme = "http" if not self._secure else "https"
            public_url = blob.public_url.replace(
                "https://storage.googleapis.com",
                f"{_scheme}://{self._external_hostname}",
            )
            return public_url
        url = blob.generate_signed_url(
            expiration=expires, method=_method, content_type=content_type
        )
        return url

    def copy_object(
        self,
        source_bucket_name: str,
        source_name: str,
        destination_bucket_name: str,
        destination_name: str,
    ) -> None:
        if not self.object_exists(source_bucket_name, source_name):
            raise StorageException(
                "object {0} does not exist in bucket {1}".format(
                    source_name, source_bucket_name
                )
            )
        storage_client = self._client()

        source_bucket = storage_client.bucket(source_bucket_name)
        source_blob = source_bucket.blob(source_name)
        destination_bucket = storage_client.bucket(destination_bucket_name)
        destination_blob = destination_bucket.blob(destination_name)
        logger.debug(
            "copying %s/%s to %s/%s",
            source_bucket_name,
            source_name,
            destination_bucket_name,
            destination_name,
        )
        rewrite_token = False
        while True:
            (
                rewrite_token,
                bytes_rewritten,
                bytes_to_rewrite,
            ) = destination_blob.rewrite(source_blob, token=rewrite_token)
            logger.debug(
                "...progress so far: %s/%s bytes...",
                bytes_rewritten,
                bytes_to_rewrite,
            )
            if not rewrite_token:
                break

    def rename_object(
        self,
        bucket_name: str,
        name: str,
        new_name: str,
    ) -> None:
        if not self.object_exists(bucket_name, name):
            raise StorageException(
                "object {0} does not exist in bucket {1}".format(
                    name, bucket_name
                )
            )
        bucket = self._client().bucket(bucket_name)
        blob = bucket.blob(name)
        bucket.rename_blob(blob, new_name)

    def md5_checksum(self, bucket_name: str, name: str) -> str:
        if not self.object_exists(bucket_name, name):
            raise StorageException(
                "object {0} does not exist in bucket {1}".format(
                    name, bucket_name
                )
            )
        bucket = self._client().bucket(bucket_name)
        blob = bucket.get_blob(name)
        return hexlify(b64decode(blob.md5_hash)).decode("utf-8")
