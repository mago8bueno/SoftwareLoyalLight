# backend/app/api/auth.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from datetime import datetime, timezone

from app.db.supabase import supabase
from app.utils.auth import create_jwt_token, verify_password, decode_jwt_debug, test_jwt_secret
from app.core.settings import settings

router = APIRouter()
security = HTTPBearer()

# =========================
# MODELOS
# =========================
class LoginRequest(BaseModel):
    email: str
    password: str

# =========================
# ENDPOINT LOGIN
# =========================
@router.post("/login")
async def login(request: LoginRequest):
    """Endpoint de login principal"""
    try:
        # Buscar usuario en Supabase
        user_result = supabase.table("users").select("*").eq("email", request.email).single().execute()
        
        if not user_result.data:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        
        user = user_result.data
        
        # Verificar contraseña
        if not verify_password(request.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        
        # Crear JWT token
        token = create_jwt_token({"user_id": user["id"], "email": user["email"]})
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user.get("name"),
                "role": user.get("role", "user")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# =========================
# ENDPOINT DEBUG JWT
# =========================
@router.post("/debug-jwt", tags=["debug"])
async def debug_jwt_token(payload: dict):
    """
    Endpoint de debug para diagnosticar problemas JWT.
    Payload: {"token": "jwt_token_here"}
    """
    try:
        token = payload.get("token", "").strip()
        if not token:
            return {"error": "Token requerido en payload"}
        
        # Info del secreto JWT
        secret_info = test_jwt_secret()
        
        # Decodificar token sin validar firma
        token_info = decode_jwt_debug(token)
        
        # Info de configuración 
        settings_info = {
            "has_jwt_secret": bool(getattr(settings, "JWT_SECRET", None)),
            "has_supabase_key": bool(getattr(settings, "SUPABASE_KEY", None)),
            "jwt_secret_length": len(str(getattr(settings, "JWT_SECRET", ""))) if getattr(settings, "JWT_SECRET", None) else 0,
            "supabase_key_length": len(str(getattr(settings, "SUPABASE_KEY", ""))) if getattr(settings, "SUPABASE_KEY", None) else 0,
        }
        
        return {
            "secret_config": secret_info,
            "token_analysis": token_info, 
            "settings_info": settings_info,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "type": type(e).__name__,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
