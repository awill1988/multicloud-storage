from json import dumps
from typing import Optional
from datetime import timedelta

from minio import Minio
from minio.deleteobjects import DeleteObject
from minio.error import S3Error

from .storage import StorageClient
from .exception import StorageException
from .http import HttpMethod
from .config import config


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

    _secure: bool = False
    _minio_client: Minio = None
    _endpoint: Optional[str] = None
    _external_hostname: Optional[str] = None

    @classmethod
    def configure(cls) -> None:
        s3_config = {
            key: value
            for key, value in config().items()
            if key
            in (
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
                "AWS_REGION",
                "S3_ENDPOINT",
                "STORAGE_EXTERNAL_HOSTNAME",
            )
        }
        cls._endpoint = s3_config["S3_ENDPOINT"]
        cls._external_hostname = (
            s3_config["STORAGE_EXTERNAL_HOSTNAME"]
            if s3_config["STORAGE_EXTERNAL_HOSTNAME"] is not None
            else cls._endpoint
        )
        cls._minio_client = Minio(
            cls._endpoint,
            access_key=s3_config["AWS_ACCESS_KEY_ID"],
            secret_key=s3_config["AWS_SECRET_ACCESS_KEY"],
            session_token=None,
            secure=cls._secure,
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
        if not self.bucket_exists(bucket_name):
            raise StorageException(
                "bucket {0} does not exist".format(bucket_name)
            )
        self._minio_client.put_object(
            bucket_name,
            name,
            data,
            size,
            content_type,
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

    def get_presigned_url(
        self,
        bucket_name: str,
        name: str,
        method: HttpMethod,
        expires: Optional[timedelta],
        _: Optional[str],
    ) -> str:
        if not self.bucket_exists(bucket_name):
            raise StorageException(
                "bucket {0} does not exist".format(bucket_name)
            )
        return self._minio_client.get_presigned_url(
            method=method,
            bucket_name=bucket_name,
            object_name=name,
            expires=expires,
        ).replace(self._endpoint, self._external_hostname)
