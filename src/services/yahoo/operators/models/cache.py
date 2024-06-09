from enum import Enum


class Cache(str, Enum):
    REUSE = "REUSE"
    SKIP = "SKIP"
    APPEND = "APPEND"
