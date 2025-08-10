# backend/app/api/auth.py  
from __future__ import annotations  
  
from datetime import datetime, timedelta, timezone  
  
from fastapi import APIRouter, HTTPException  
from pydantic import BaseModel, EmailStr  
from passlib.context import CryptContext  
import jwt  
  
from app.db.supabase import supabase  # cliente Supabase ya configurado  
from app.core.settings import settings  
  
router = APIRouter()  
  
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")  
  
JWT_ALG = "HS256"  
JWT_TTL_HOURS = 24  # caducidad del token  
  
def _jwt_secret() -> str:  
    # Usa JWT_SECRET si existe; si no, SUPABASE_KEY como fallback  
    return (getattr(settings, "JWT_SECRET", None) or settings.SUPABASE_KEY)  
  
  
class LoginIn(BaseModel):  
    email: EmailStr  
    password: str  
  
  
class UserOut(BaseModel):  
    id: str  
    email: EmailStr  
    name: str | None = None  
  
  
class LoginOut(BaseModel):  
    access_token: str  
    token_type: str = "bearer"  
    user: UserOut  
  
  
@router.post("/login/", response_model=LoginOut)  
def login(payload: LoginIn):  
    # Buscar usuario por email  
    res = (  
        supabase.table("users")  
        .select("id,email,hashed_password,name")  
        .eq("email", str(payload.email))  
        .single()  
        .execute()  
    )  
    row = getattr(res, "data", None)  
    if not row or not row.get("hashed_password"):  
        raise HTTPException(status_code=401, detail="Invalid credentials")  
  
    # Verificar contraseña con bcrypt  
    if not pwd_ctx.verify(payload.password, row["hashed_password"]):  
        raise HTTPException(status_code=401, detail="Invalid credentials")  
  
    user = {"id": row["id"], "email": row["email"], "name": row.get("name")}  
  
    # Generar JWT  
    now = datetime.now(timezone.utc)  
    claims = {  
        "sub": row["id"],  
        "email": row["email"],  
        "iat": int(now.timestamp()),  
        "exp": int((now + timedelta(hours=JWT_TTL_HOURS)).timestamp()),  
    }  
    token = jwt.encode(claims, _jwt_secret(), algorithm=JWT_ALG)  
  
    return {"access_token": token, "token_type": "bearer", "user": user}
