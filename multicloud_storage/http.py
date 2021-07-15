from enum import Enum

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal


class HttpMethod(Enum):
    GET: Literal["GET"] = "GET"
    PUT: Literal["PUT"] = "PUT"
