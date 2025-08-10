# backend/app/api/auth.py  
from fastapi import APIRouter, HTTPException  
from pydantic import BaseModel  
from passlib.context import CryptContext  
import jwt  
from datetime import datetime, timedelta  
  
from app.db.supabase import supabase  # cliente Supabase ya configurado  
from app.core.settings import settings  
  
router = APIRouter()  
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")  
  
  
class LoginIn(BaseModel):  
    email: str  
    password: str  
  
  
class LoginOut(BaseModel):  
    access_token: str  
    token_type: str = "bearer"  
    user: dict | None = None  
  
  
@router.post("/login/", response_model=LoginOut)  
def login(payload: LoginIn):  
    # Buscar usuario por email  
    res = (  
        supabase.table("users")  
        .select("id,email,hashed_password,name")  
        .eq("email", payload.email)  
        .single()  
        .execute()  
    )  
    row = getattr(res, "data", None)  
    if not row or not row.get("hashed_password"):  
        raise HTTPException(status_code=401, detail="Invalid credentials")  
  
    # Verificar contraseña con bcrypt  
    if not pwd_ctx.verify(payload.password, row["hashed_password"]):  
        raise HTTPException(status_code=401, detail="Invalid credentials")  
  
    # Generar JWT real usando la misma clave que usa la validación  
    user = {"id": row["id"], "email": row["email"], "name": row.get("name")}  
    token_data = {  
        "email": row["email"],  
        "user_id": row["id"],  
        "exp": datetime.utcnow() + timedelta(hours=24)  
    }  
    token = jwt.encode(token_data, settings.SUPABASE_KEY, algorithm="HS256")  
      
    return {"access_token": token, "token_type": "bearer", "user": user}
