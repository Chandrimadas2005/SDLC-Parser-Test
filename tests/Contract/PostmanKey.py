from enum import StrEnum


class PostmanKey(StrEnum):
    """Keys of the Postman collection format (v2.1) that the contract test reads."""

    ITEM = "item"
    REQUEST = "request"
    METHOD = "method"
    URL = "url"
    RAW = "raw"
    VARIABLE = "variable"
    KEY = "key"
    VALUE = "value"
