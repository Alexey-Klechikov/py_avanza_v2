from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Exchange(BaseModel):
    name: str
    code: str

    open: Optional[datetime]
    close: Optional[datetime]
