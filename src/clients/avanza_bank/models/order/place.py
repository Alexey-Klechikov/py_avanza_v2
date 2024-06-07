from typing import List, Optional

from pydantic import BaseModel, Field


class PlaceOrderResponse(BaseModel):
    order_request_status: str = Field(alias="orderRequestStatus")
    message: str
    message_code: Optional[str] = Field(alias="messageCode", default=None)
    parameters: List[str]
    order_id: Optional[str] = Field(alias="orderId", default=None)
