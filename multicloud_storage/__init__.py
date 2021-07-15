"""An amazing sample package!"""

__version__ = "0.0.7"

from .gcs import GCS
from .minio import S3
from .storage import Storage
from .exception import StorageException
from .http import HttpMethod

__all__ = ["GCS", "S3", "Storage", "HttpMethod", "StorageException"]
