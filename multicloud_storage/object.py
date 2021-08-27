from typing import Union
from google.cloud.storage import Blob
from minio.datatypes import Object
from datetime import datetime
from .exception import StorageException

StorageObject = Union[Blob, Object]


def last_modified(obj: StorageObject) -> datetime:
    if type(obj) == Blob:
        return obj.updated
    if type(obj) == Object:
        return obj.last_modified
    raise StorageException("Invalid object type provided")


def size(obj: StorageObject) -> int:
    if type(obj) == Blob:
        return obj.size
    if type(obj) == Object:
        return obj.size
    raise StorageException("Invalid object type provided")


def name(obj: StorageObject) -> str:
    if type(obj) == Blob:
        return obj.name
    if type(obj) == Object:
        return obj.object_name
    raise StorageException("Invalid object type provided")
