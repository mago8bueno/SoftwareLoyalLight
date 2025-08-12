# backend/app/models/client.py - Schemas Pydantic para Cliente

from pydantic import BaseModel, validator
from typing import Optional

class ClientBase(BaseModel):
    name: str
    email: Optional[str] = None  # ← CORREGIDO: usar str en lugar de EmailStr
    phone: Optional[str] = None

    # ← AÑADIR: Validador personalizado para email más permisivo
    @validator('email')
    def validate_email(cls, v):
        if v is not None and v.strip():
            # Validación básica de email
            import re
            if not re.match(r'^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$', v):
                raise ValueError('Email inválido')
        return v

class ClientCreate(ClientBase):
    pass  # Reusar campos de ClientBase

class ClientOut(ClientBase):
    id: str  # ← CORREGIDO: usar str en lugar de UUID para consistencia
    owner_id: str  # ← AÑADIR: campo owner_id que usa el backend
    created_at: Optional[str] = None

    class Config:
        from_attributes = True  # ← CORREGIDO: sintaxis Pydantic v2
