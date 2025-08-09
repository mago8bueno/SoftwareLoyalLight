# purchase.py - Schemas Pydantic para Purchase

from pydantic import BaseModel, conint, condecimal
from uuid import UUID

class PurchaseBase(BaseModel):
    client_id: UUID
    item_id: UUID
    quantity: conint(gt=0)

class PurchaseCreate(PurchaseBase):
    pass

class PurchaseOut(PurchaseBase):
    id: UUID
    total_price: condecimal(decimal_places=2, ge=0)
    purchased_at: str

    class Config:
        orm_mode = True