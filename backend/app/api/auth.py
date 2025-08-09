# backend/app/api/auth.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class LoginIn(BaseModel):
    email: str
    password: str

class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict | None = None

# 👇 Añadida barra final al endpoint
@router.post("/login/", response_model=LoginOut)
def login(payload: LoginIn):
    # DEMO: credenciales fijas de desarrollo
    if payload.email == "admin@example.com" and payload.password == "admin123":
        return {
            "access_token": "dev-token-123",  # en producción genera JWT
            "token_type": "bearer",
            "user": {"email": payload.email}
        }
    raise HTTPException(status_code=401, detail="Invalid credentials")
