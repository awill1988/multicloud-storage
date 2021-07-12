from .client import StorageClient


class Storage:
    """
    Storage.

    The Storage defines the interface for the "control" part of the two
    class hierarchies. It maintains a reference to an object of the
    Implementation hierarchy and delegates all of the real work to this object.
    """

    def __init__(
        self,
        client: StorageClient,
    ) -> None:
        self._client = client
        self._client.configure()

    def bucket_exists(self, name: str) -> bool:
        return self._client.bucket_exists(name)

    def make_bucket(self, name: str) -> None:
        return self._client.make_bucket(name)

    def remove_bucket(self, name: str) -> None:
        return self._client.remove_bucket(name)

    def put_object(
        self,
        bucket_name: str,
        name: str,
        data: object,
        size: int,
        content_type: str = "application/octet-stream",
    ) -> None:
        return self._client.put_object(
            bucket_name, name, data, size, content_type
        )

    def object_exists(self, bucket_name: str, name: str) -> bool:
        return self._client.object_exists(bucket_name, name)

    def put_object_presigned_url(self, bucket_name: str, name: str) -> str:
        return self._client.put_object_presigned_url(bucket_name, name)

    def get_object_presigned_url(self, bucket_name: str, name: str) -> str:
        return self._client.get_object_presigned_url(bucket_name, name)
