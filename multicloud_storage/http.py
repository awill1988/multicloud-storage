from enum import Enum

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal


class HttpMethod(Enum):
    """HttpMethod is an enum class for HTTP Methods."""

    GET: Literal["GET"] = "GET"
    PUT: Literal["PUT"] = "PUT"
