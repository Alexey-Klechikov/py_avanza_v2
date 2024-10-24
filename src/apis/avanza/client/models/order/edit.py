from pydantic import BaseModel, Field


class EditOrderResponse(BaseModel):
    order_request_status: str = Field(alias="orderRequestStatus")
    message: str
    message_code: str | None = Field(alias="messageCode", default=None)
    parameters: list[str]
    order_id: str | None = Field(alias="orderId", default=None)
