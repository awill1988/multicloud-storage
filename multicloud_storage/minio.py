from datetime import datetime, timedelta
from json import dumps
from typing import Iterator, Optional, Union
from urllib.parse import urlsplit
from io import BytesIO
from minio import Minio
from minio.commonconfig import CopySource
from minio.credentials import Credentials
from minio.deleteobjects import DeleteObject
from minio.error import S3Error
from minio.signer import presign_v4
from minio.datatypes import Object
from .config import config
from .exception import StorageException
from .http import HttpMethod
from .storage import StorageClient
from .log import logger


def _credentials(
    access_key: str, secret_key: str, session_token: Optional[str]
) -> Credentials:
    return Credentials(access_key, secret_key, session_token)


def _public_bucket_acl(bucket_name: str) -> str:
    """
    Example anonymous read-write bucket policy.
    """
    return dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": [
                        "s3:GetBucketLocation",
                        "s3:ListBucket",
                        "s3:ListBucketMultipartUploads",
                    ],
                    "Resource": "arn:aws:s3:::{0}".format(bucket_name),
                },
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject",
                        "s3:ListMultipartUploadParts",
                        "s3:AbortMultipartUpload",
                    ],
                    "Resource": "arn:aws:s3:::{0}/*".format(bucket_name),
                },
            ],
        }
    )


class S3(StorageClient):
    """
    S3.
    """

    def __init__(self) -> None:
        super().__init__()
        self._secure: bool = False
        self._minio_client: Minio = None
        self._endpoint: Optional[str] = None
        self._external_hostname: Optional[str] = None
        self._credentials: Credentials = None
        self._region: str = "us-east-1"

    def configure(self) -> None:
        s3_config = {
            key: value
            for key, value in config().items()
            if key
            in (
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
                "AWS_SESSION_TOKEN",
                "AWS_REGION",
                "S3_ENDPOINT",
                "STORAGE_EXTERNAL_HOSTNAME",
            )
        }
        self._endpoint = s3_config["S3_ENDPOINT"]
        self._region = (
            s3_config["AWS_REGION"]
            if s3_config["AWS_REGION"] is not None
            else self._region
        )
        self._external_hostname = (
            s3_config["STORAGE_EXTERNAL_HOSTNAME"]
            if s3_config["STORAGE_EXTERNAL_HOSTNAME"] is not None
            else self._endpoint
        )
        self._credentials = _credentials(
            s3_config["AWS_ACCESS_KEY_ID"],
            s3_config["AWS_SECRET_ACCESS_KEY"],
            None,
        )
        self._minio_client = Minio(
            self._endpoint,
            access_key=self._credentials.access_key,
            secret_key=self._credentials.secret_key,
            session_token=None,
            secure=self._secure,
            region=s3_config["AWS_REGION"],
        )

    def bucket_exists(self, name: str) -> bool:
        return self._minio_client.bucket_exists(name)

    def make_bucket(self, name: str) -> None:
        if self.bucket_exists(name):
            raise StorageException("bucket {0} already exists".format(name))

        self._minio_client.make_bucket(name)
        self._minio_client.set_bucket_policy(name, _public_bucket_acl(name))

    def remove_bucket(self, name: str) -> None:
        if not self.bucket_exists(name):
            raise StorageException("bucket {0} does not exist".format(name))
        # Empty all objects
        delete_object_list = map(
            lambda x: DeleteObject(x.object_name),
            self._minio_client.list_objects(name, "/", recursive=True),
        )
        errors = self._minio_client.remove_objects(name, delete_object_list)
        for error in errors:
            print("error occured when deleting object", error)
        self._minio_client.remove_bucket(name)

    def delete_object(self, bucket_name: str, name: str) -> None:
        if not self.bucket_exists(bucket_name):
            raise StorageException(
                "bucket {0} does not exist".format(bucket_name)
            )
        self._minio_client.remove_object(bucket_name, name)

    def put_object(
        self,
        bucket_name: str,
        name: str,
        data: object,
        size: int,
    ) -> None:
        if not self.bucket_exists(bucket_name):
            raise StorageException(
                "bucket {0} does not exist".format(bucket_name)
            )
        self._minio_client.put_object(
            bucket_name,
            name,
            data,
            size,
        )

    def object_exists(self, bucket_name: str, name: str) -> bool:
        if not self.bucket_exists(bucket_name):
            raise StorageException(
                "bucket {0} does not exist".format(bucket_name)
            )
        try:
            self._minio_client.stat_object(bucket_name, name)
            return True
        except S3Error as err:
            msg = "Minio Client Error: {0} (code: {1})".format(
                err.message, err.code
            )
            if err.code == "NoSuchKey":
                return False
            raise StorageException(msg) from None

    def get_object(self, bucket_name: str, name: str) -> BytesIO:
        if not self.object_exists(bucket_name, name):
            raise StorageException(
                "object {0} does not exist in bucket {1}".format(
                    name, bucket_name
                )
            )
        data = None
        try:
            response = self._minio_client.get_object(bucket_name, name)
            # Read data from response.
            data = response.data
        finally:
            response.close()
            response.release_conn()
        return BytesIO(data)

    def get_presigned_url(
        self,
        bucket_name: str,
        name: str,
        method: Union[str, HttpMethod],
        expires: Optional[timedelta],
        _: str = None,
        use_hostname: str = None,
        secure: bool = None,
    ) -> str:
        if not self.bucket_exists(bucket_name):
            raise StorageException(
                "bucket {0} does not exist".format(bucket_name)
            )
        if expires is None:
            raise StorageException("expires must be defined")
        _secure = secure if secure is not None else self._secure
        _hostname = (
            self._external_hostname if use_hostname is None else use_hostname
        )
        _method = method.value if not isinstance(method, str) else method
        _scheme = "https" if _secure else "http"
        if _method in ("GET", "HEAD") and not self.object_exists(
            bucket_name, name
        ):
            raise StorageException(
                "object {0} does not exist in bucket {1}".format(
                    name, bucket_name
                )
            )
        url = urlsplit(
            "{}://{}/{}/{}".format(
                _scheme,
                _hostname,
                bucket_name,
                name,
            ),
        )
        logger.debug("signing the url %s", url)
        now = datetime.now()
        signed_url = presign_v4(
            _method,
            url,
            region=self._region,
            credentials=self._credentials,
            expires=int(expires.total_seconds()),
            date=now,
        )

        # use the "external" minio client so that signed urls work properly
        return signed_url.geturl()

    # TODO Pagination
    def list_objects(
        self, bucket_name: str, prefix: Optional[str]
    ) -> Iterator[Object]:
        if not self.bucket_exists(bucket_name):
            raise StorageException(
                "bucket {0} does not exist".format(bucket_name)
            )
        return self._minio_client.list_objects(bucket_name, prefix)

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
        self._minio_client.copy_object(
            destination_bucket_name,
            destination_name,
            CopySource(source_bucket_name, source_name),
        )

    def rename_object(
        self,
        bucket_name: str,
        name: str,
        new_name: str,
    ) -> None:
        self.copy_object(
            bucket_name,
            name,
            bucket_name,
            new_name,
        )
        self.delete_object(bucket_name, name)

    def md5_checksum(self, bucket_name: str, name: str) -> str:
        if not self.object_exists(bucket_name, name):
            raise StorageException(
                "object {0} does not exist in bucket {1}".format(
                    name, bucket_name
                )
            )
        metadata = self._minio_client.stat_object(bucket_name, name)
        return metadata.etag
