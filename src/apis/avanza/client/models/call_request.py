from avanza import constants
from pydantic import BaseModel, field_validator


class CallRequest(BaseModel):
    path: str
    method: constants.HttpMethod | str
    options: list | dict | None = None

    @field_validator("method", mode="before")
    @classmethod
    def parse_method(cls, v):
        if isinstance(v, constants.HttpMethod):
            return v

        return constants.HttpMethod[v.upper()]
