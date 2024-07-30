from typing import Dict, List, Optional, Union

from avanza import constants
from pydantic import BaseModel, field_validator


class CallRequest(BaseModel):
    path: str
    method: Union[constants.HttpMethod, str]
    options: Optional[Union[List, Dict]] = None

    @field_validator("method", mode="before")
    @classmethod
    def parse_method(cls, v):
        if isinstance(v, constants.HttpMethod):
            return v

        return constants.HttpMethod[v.upper()]
