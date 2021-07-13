from __future__ import (
    annotations,
)
from abc import (
    ABC,
    abstractmethod,
)
from datetime import timedelta
from typing import Optional
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

    @classmethod
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
    def put_object(
        self,
        bucket_name: str,
        name: str,
        data: object,
        size: int,
        content_type: str,
    ) -> None:
        pass

    @abstractmethod
    def object_exists(self, bucket_name: str, name: str) -> bool:
        pass

    @abstractmethod
    def get_presigned_url(
        self,
        bucket_name: str,
        name: str,
        method: HttpMethod,
        expires: Optional[timedelta],
        content_type: Optional[str],
    ) -> str:
        pass
