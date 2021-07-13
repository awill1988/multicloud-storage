from enum import Enum
from typing import Literal


class HttpMethod(Enum):
    GET: Literal["GET"] = "GET"
    PUT: Literal["PUT"] = "PUT"
