# item.py - Schemas Pydantic para Item

from pydantic import BaseModel, condecimal, conint
from uuid import UUID

class ItemBase(BaseModel):
    name: str
    description: str
    price: condecimal(decimal_places=2, ge=0)
    stock: conint(ge=0)

class ItemCreate(ItemBase):
    pass

class ItemOut(ItemBase):
    id: UUID
    created_at: str

    class Config:
        orm_mode = True