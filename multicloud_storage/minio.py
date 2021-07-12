from datetime import timedelta
from json import dumps

from minio import Minio
from minio.deleteobjects import DeleteObject
from minio.error import S3Error

from .storage import StorageClient
from .exception import StorageException


def human_read_to_byte(h_input: str) -> int:
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    size = h_input.split()  # divide '1 GB' into ['1', 'GB']
    num, unit = int(size[0]), size[1]
    idx = size_name.index(
        unit
    )  # index in list of sizes determines power to raise it to
    factor = (
        1024 ** idx
    )  # ** is the "exponent" operator - you can use it instead of math.pow()
    return num * factor


# Example anonymous read-write bucket policy.
def _public_bucket_acl(bucket_name: str) -> str:
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

    def __init__(
        self,
        endpoint,
        access_key=None,
        secret_key=None,
        session_token=None,
        secure=True,
        region=None,
        http_client=None,
        credentials=None,
    ) -> None:
        super().__init__()
        self._minio_client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            session_token=session_token,
            secure=secure,
            region=region,
            http_client=http_client,
            credentials=credentials,
        )

    def configure(self) -> None:
        return

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

    def put_object_presigned_url(self, bucket_name: str, name: str) -> str:
        if not self.bucket_exists(bucket_name):
            raise StorageException(
                "bucket {0} does not exist".format(bucket_name)
            )
        return self._minio_client.presigned_put_object(
            bucket_name,
            name,
            expires=timedelta(hours=2),
        )

    def get_object_presigned_url(self, bucket_name: str, name: str) -> str:
        if not self.bucket_exists(bucket_name):
            raise StorageException(
                "bucket {0} does not exist".format(bucket_name)
            )
        return self._minio_client.presigned_get_object(
            bucket_name,
            name,
            expires=timedelta(hours=2),
        )
