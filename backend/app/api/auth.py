# backend/app/api/auth.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

# --- Dependencias externas necesarias ---
# pip install passlib[bcrypt] PyJWT
from passlib.context import CryptContext
import jwt

# --- Imports de tu proyecto ---
from app.db.supabase import supabase
from app.core.settings import settings

router = APIRouter()
__all__ = ["router"]

# -------- Config JWT / Password --------
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# -------- Modelos --------
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenPayload(BaseModel):
    user_id: str
    email: str
    exp: int


class RefreshRequest(BaseModel):
    token: str  # access token vigente (no refresco separado)


# -------- Utilidades --------
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(data: Dict[str, Any],
                        expires_delta: Optional[timedelta] = None) -> str:
    if not getattr(settings, "JWT_SECRET", None):
        raise RuntimeError("JWT_SECRET no configurado en settings")
    to_encode = data.copy()
    expire = _utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    if not getattr(settings, "JWT_SECRET", None):
        raise RuntimeError("JWT_SECRET no configurado en settings")
    try:
        decoded = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        return TokenPayload(**decoded)  # valida estructura mínima
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token inválido")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(plain_password, password_hash or "")
    except Exception:
        return False


def _extract_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    parts = auth.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Falta encabezado Authorization Bearer")


# 🔧 DEPENDENCIA HTTPS - Se ejecuta antes del endpoint
def force_https(request: Request):
    """Dependencia que fuerza HTTPS"""
    if request.url.scheme == "http":
        https_url = request.url.replace(scheme="https")
        print(f"🔒 DEPENDENCIA HTTPS: REDIRIGIENDO HTTP → HTTPS: {request.url} → {https_url}")
        return RedirectResponse(url=str(https_url), status_code=301)
    return None


# -------- Endpoints --------
@router.get("/test-https")
async def test_https(request: Request):
    """Endpoint de prueba para verificar HTTPS"""
    return {
        "scheme": request.url.scheme,
        "url": str(request.url),
        "is_http": request.url.scheme == "http",
        "timestamp": datetime.now().isoformat()
    }

@router.post("/login")
async def login(request: Request, request_body: LoginRequest):
    """
    Login por email + password: devuelve access_token (HS256) de 24h.
    """
    # 🔧 FIX HTTPS: Redirigir HTTP a HTTPS
    if request.url.scheme == "http":
        https_url = request.url.replace(scheme="https")
        print(f"🔒 LOGIN: REDIRIGIENDO HTTP → HTTPS: {request.url} → {https_url}")
        return RedirectResponse(url=str(https_url), status_code=301)
    
    try:
        # 1) Buscar usuario
        resp = (
            supabase.table("users")
            .select("*")
            .eq("email", request_body.email)
            .single()
            .execute()
        )
        user = getattr(resp, "data", None)
        if not user:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")

        # 2) Verificar contraseña
        if not verify_password(request_body.password, user.get("password_hash", "")):
            raise HTTPException(status_code=401, detail="Credenciales inválidas")

        # 3) Crear token
        token = create_access_token(
            {"user_id": user["id"], "email": user["email"]}
        )

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
        # Logea en tu plataforma (Railway, etc.) si procede
        # print(f"[login] error: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/me")
async def me(request: Request):
    """
    Lee Authorization: Bearer <token>, valida y devuelve el usuario.
    """
    token = _extract_bearer_token(request)
    payload = decode_token(token)

    # Relee usuario por seguridad (puede haber cambiado rol/nombre)
    resp = (
        supabase.table("users")
        .select("id,email,name,role")
        .eq("id", payload.user_id)
        .single()
        .execute()
    )
    user = getattr(resp, "data", None)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    return {"user": user, "token_valid": True}


@router.post("/refresh")
async def refresh(body: RefreshRequest):
    """
    Reemite un token nuevo a partir de uno aún válido (mismo payload, exp reiniciado).
    No usa refresh-tokens separados (simple y suficiente para MVP).
    """
    payload = decode_token(body.token)
    new_token = create_access_token({"user_id": payload.user_id, "email": payload.email})
    return {"access_token": new_token, "token_type": "bearer"}


@router.post("/debug-jwt", tags=["debug"])
async def debug_jwt_token(payload: dict):
    """
    DEBUG: enviar {"token": "<jwt>"} para inspección básica.
    NO usar en producción abierta.
    """
    try:
        token = (payload.get("token") or "").strip()
        if not token:
            return {"error": "Token requerido en payload"}

        info: Dict[str, Any] = {"now": _utcnow().isoformat()}
        try:
            decoded = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM],
                                 options={"verify_signature": True, "verify_exp": True})
            info["decoded"] = decoded
            info["valid"] = True
        except jwt.ExpiredSignatureError:
            info["valid"] = False
            info["error"] = "expired"
            info["decoded_noverify"] = jwt.decode(token, options={"verify_signature": False})
        except jwt.InvalidTokenError as e:
            info["valid"] = False
            info["error"] = f"invalid: {type(e).__name__}"

        info["settings"] = {
            "has_jwt_secret": bool(getattr(settings, "JWT_SECRET", None)),
            "jwt_secret_length": len(str(getattr(settings, "JWT_SECRET", ""))) if getattr(settings, "JWT_SECRET", None) else 0,
            "has_supabase_key": bool(getattr(settings, "SUPABASE_KEY", None)),
        }
        return info
    except Exception as e:
        return {
            "error": str(e),
            "type": type(e).__name__,
            "timestamp": _utcnow().isoformat(),
        }
