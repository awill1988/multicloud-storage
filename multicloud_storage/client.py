from __future__ import (
    annotations,
)
from abc import (
    ABC,
    abstractmethod,
)
from datetime import timedelta
from multicloud_storage.object import StorageObject
from typing import Iterator, Optional, Union
from io import BytesIO
from .http import HttpMethod


class StorageClient(ABC):
    """
    StorageClient.

    The StorageClient defines the interface for all implementation classes. It
    doesn't have to match the Abstraction's interface. In fact, the two
    interfaces can be entirely different. Typically the Implementation interface
    provides only primitive operations, while the Abstraction defines higher-
    level operations based on those primitives.
    """

    @abstractmethod
    def configure(cls) -> None:
        pass

    @abstractmethod
    def bucket_exists(self, name: str) -> bool:
        pass

    @abstractmethod
    def make_bucket(self, name: str) -> None:
        pass

    @abstractmethod
    def remove_bucket(self, name: str) -> None:
        pass

    @abstractmethod
    def get_object(
        self,
        bucket_name: str,
        name: str,
    ) -> BytesIO:
        pass

    @abstractmethod
    def list_objects(
        self,
        bucket_name: str,
        prefix: Optional[str],
    ) -> Iterator[StorageObject]:
        pass

    @abstractmethod
    def put_object(
        self,
        bucket_name: str,
        name: str,
        data: BytesIO,
        size: int,
    ) -> None:
        pass

    @abstractmethod
    def copy_object(
        self,
        source_bucket_name: str,
        source_name: str,
        destination_bucket_name: str,
        destination_name: str,
    ) -> None:
        pass

    @abstractmethod
    def rename_object(
        self,
        bucket_name: str,
        name: str,
        new_name: str,
    ) -> None:
        pass

    @abstractmethod
    def object_exists(self, bucket_name: str, name: str) -> bool:
        pass

    @abstractmethod
    def delete_object(self, bucket_name: str, name: str) -> None:
        pass

    @abstractmethod
    def get_presigned_url(
        self,
        bucket_name: str,
        name: str,
        method: Union[str, HttpMethod],
        expires: Optional[timedelta],
        content_type: Optional[str],
        use_hostname: Optional[str],
        secure: Optional[bool],
    ) -> str:
        pass

    @abstractmethod
    def md5_checksum(self, bucket_name: str, name: str) -> str:
        pass
