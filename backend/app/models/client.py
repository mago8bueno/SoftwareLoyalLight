# client.py - Schemas Pydantic para Cliente

from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID

class ClientBase(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

class ClientCreate(ClientBase):
    pass  # Reusar campos de ClientBase

class ClientOut(ClientBase):
    id: UUID
    created_at: str

    class Config:
        orm_mode = True