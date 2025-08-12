# backend/app/models/client.py - Schemas Pydantic para Cliente

from pydantic import BaseModel, validator
from typing import Optional

class ClientBase(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None

    @validator("email")
    def validate_email(cls, v):
        if v is not None and v.strip():
            import re
            if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", v):
                raise ValueError("Email inválido")
        return v

class ClientCreate(ClientBase):
    pass

class ClientOut(ClientBase):
    id: str
    owner_id: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True
