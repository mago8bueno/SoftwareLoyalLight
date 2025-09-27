# backend/app/api/auth.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone

# Define el router ANTES de cualquier import pesado
router = APIRouter()
__all__ = ["router"]  # export explícito

# ---- Modelos ----
class LoginRequest(BaseModel):
    email: str
    password: str

# ---- Endpoints ----
@router.post("/login")
async def login(request: LoginRequest):
    """
    Endpoint de login principal.
    Lazy-import para evitar romper el import del módulo si falta alguna dependencia.
    """
    try:
        from app.db.supabase import supabase
        from app.utils.auth import create_jwt_token, verify_password

        # Buscar usuario en Supabase
        user_result = (
            supabase.table("users")
            .select("*")
            .eq("email", request.email)
            .single()
            .execute()
        )

        if not user_result or not user_result.data:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")

        user = user_result.data

        # Verificar contraseña
        if not verify_password(request.password, user.get("password_hash", "")):
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
                "role": user.get("role", "user"),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        # Log opcional aquí
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/debug-jwt", tags=["debug"])
async def debug_jwt_token(payload: dict):
    """
    Endpoint de debug para diagnosticar problemas JWT.
    Payload: {"token": "jwt_token_here"}
    """
    try:
        from app.utils.auth import decode_jwt_debug, test_jwt_secret
        from app.core.settings import settings

        token = (payload.get("token") or "").strip()
        if not token:
            return {"error": "Token requerido en payload"}

        secret_info = test_jwt_secret()
        token_info = decode_jwt_debug(token)

        settings_info = {
            "has_jwt_secret": bool(getattr(settings, "JWT_SECRET", None)),
            "has_supabase_key": bool(getattr(settings, "SUPABASE_KEY", None)),
            "jwt_secret_length": len(str(getattr(settings, "JWT_SECRET", "")))
            if getattr(settings, "JWT_SECRET", None)
            else 0,
            "supabase_key_length": len(str(getattr(settings, "SUPABASE_KEY", "")))
            if getattr(settings, "SUPABASE_KEY", None)
            else 0,
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
