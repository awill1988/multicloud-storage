from base64 import b64decode
from binascii import hexlify
from datetime import timedelta
from io import BytesIO
from typing import Iterator, List, Optional, Union

from google.cloud.storage import Client, Blob

from .client import StorageClient
from .config import config
from .exception import StorageException
from .http import HttpMethod
from .log import logger


class GCS(StorageClient):
    """
    GCS.
    """

    def __init__(self, project: str = None) -> None:
        super().__init__()
        self._gcs_client: Client = None
        self._use_public_urls: Optional[bool] = None
        self._emulator_hostname: Optional[str] = None
        self._external_hostname: Optional[str] = None
        self._secure: bool = True
        self._gcs_project = project

    def _project(cls):
        if cls._gcs_project is None:
            raise StorageException(
                "gcs client requires that the GOOGLE_CLOUD_PROJECT env"
                " variable is present or an option is passed"
            )
        return cls._gcs_project

    def _client(cls):
        if cls._gcs_client is None:
            raise StorageException("gcs client has not been configured")
        return cls._gcs_client

    def configure(self) -> None:
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

        self._gcs_project = (
            gcs_config["GOOGLE_CLOUD_PROJECT"]
            if self._gcs_project is None
            else self._gcs_project
        )

        self._emulator_hostname = gcs_config["STORAGE_EMULATOR_HOST"]

        self._external_hostname = (
            gcs_config["STORAGE_EXTERNAL_HOSTNAME"]
            if gcs_config["STORAGE_EXTERNAL_HOSTNAME"] is not None
            else self._emulator_hostname
        )

        if self._emulator_hostname is not None:
            if self._emulator_hostname.find("https") == -1:
                self._secure = False

            logger.debug(
                "will not sign urls due to presense of %s",
                "STORAGE_EMULATOR_HOST",
            )
            self._use_public_urls = True

        self._gcs_client = Client(project=self._gcs_project)

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
        use_hostname: Optional[str] = None,
        *_,
    ) -> str:
        if not self.bucket_exists(bucket_name):
            raise StorageException(
                "bucket {0} does not exist".format(bucket_name)
            )
        bucket = self._client().get_bucket(bucket_name)
        blob = bucket.blob(name)
        _method = method.value if not isinstance(method, str) else method
        if not blob.exists() and _method == "GET":
            raise StorageException(
                "object {0} does not exist in bucket {1}".format(
                    name, bucket_name
                )
            )
        if self._use_public_urls:
            _scheme = "http" if not self._secure else "https"
            _hostname = (
                use_hostname if use_hostname else self._external_hostname
            )
            public_url = blob.public_url.replace(
                "https://storage.googleapis.com",
                f"{_scheme}://{_hostname}",
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

    # TODO Pagination
    def list_objects(
        self, bucket_name: str, prefix: Optional[str]
    ) -> Iterator[Blob]:
        if not self.bucket_exists(bucket_name):
            raise StorageException(
                "bucket {0} does not exist".format(bucket_name)
            )
        return self._client().list_blobs(bucket_name, prefix=prefix)

    def concat_objects(
        self,
        bucket_name: str,
        destination_object: str,
        source_objects: List[str],
    ) -> None:
        if not self.object_exists(bucket_name, destination_object):
            raise StorageException(
                "object {0} does not exist in bucket {1}".format(
                    destination_object, bucket_name
                )
            )
        for obj in source_objects:
            if not self.object_exists(bucket_name, obj):
                raise StorageException(
                    "object {0} does not exist in bucket {1}".format(
                        obj, bucket_name
                    )
                )
        blob = self._client().bucket(bucket_name).blob(destination_object)
        blobs: List[Blob] = list()
        for obj in source_objects:
            blobs.append(self._client().bucket(bucket_name).blob(obj))
        blob.compose(blobs)
        return

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
