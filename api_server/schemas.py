from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CallbackBody(BaseModel):
    order_id: str = Field(example="3469aa76-2082-421b-8e54-0bb93424ae76")
    address: str = Field(example="bc1qum5dxmvs3pzfjjn2f7pfayjycn4y7rehuaarkh")
    confirmations: int = Field(2)
    txid: str = Field(example="4ac7c95fcd2a937c3b7400cfa17558c6c7f5979b7a8656"
                      "efdc0aa7207f20f56b")
    amount: Decimal = Field(example=Decimal(0.0123))


class CallbackResponse(BaseModel):
    stop: bool


class AddressIn(BaseModel):
    order_id: str = Field(max_length=50,
                          example="3469aa76-2082-421b-8e54-0bb93424ae76")
    usd_amount: Decimal = Field(default=None, example=Decimal(50))


class AddressOut(BaseModel):
    dt_created: datetime
    address: str
    order_id: str
    amount: Decimal = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(timespec='seconds')
        }
        schema_extra = {
            "example": {
                "dt_created": "2020-01-31T18:40:55+00:00",
                "address": "bc1qum5dxmvs3pzfjjn2f7pfayjycn4y7rehuaarkh",
                "order_id": "3469aa76-2082-421b-8e54-0bb93424ae76",
                "amount": Decimal("0.02")
            }
        }


class PaymentOut(BaseModel):
    dt_created: datetime
    txid: str
    vout: int
    amount: Decimal
    address: str
    order_id: str
    forward_txid: str

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(timespec='seconds')
        }
