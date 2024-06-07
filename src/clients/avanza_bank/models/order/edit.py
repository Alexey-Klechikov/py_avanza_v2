from pydantic import BaseModel, Field
from typing import List, Optional


class EditOrderResponse(BaseModel):
    order_request_status: str = Field(alias="orderRequestStatus")
    message: str
    message_code: Optional[str] = Field(alias="messageCode", default=None)
    parameters: List[str]
    order_id: Optional[str] = Field(alias="orderId", default=None)
