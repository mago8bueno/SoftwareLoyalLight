# backend/app/api/auth.py — VERSIÓN CORREGIDA Y ENDURECIDA
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import traceback

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
import jwt  # PyJWT

from app.db.supabase import supabase
from app.core.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# ==============================
# Config
# ==============================
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_ALG = "HS256"
JWT_TTL_HOURS = 24  # caducidad del token

def _jwt_secret() -> str:
    """
    Obtiene el secreto JWT con prioridad:
    1) settings.JWT_SECRET
    2) settings.SUPABASE_KEY (fallback)
    """
    if getattr(settings, "JWT_SECRET", None):
        return str(settings.JWT_SECRET)
    if getattr(settings, "SUPABASE_KEY", None):
        return str(settings.SUPABASE_KEY)
    logger.error("❌ No se encontró JWT_SECRET ni SUPABASE_KEY en settings")
    raise HTTPException(status_code=500, detail="JWT configuration error")

# ==============================
# Schemas
# ==============================
class LoginIn(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: str
    email: str
    name: str | None = None

class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# ==============================
# Health
# ==============================
@router.get("/health", tags=["auth", "debug"])
def auth_health_check():
    """
    Health check del servicio de auth:
    - Conexión Supabase básica
    - Configuración JWT disponible
    - bcrypt operativo
    """
    try:
        # Supabase: consulta mínima válida
        try:
            res = supabase.table("users").select("id", count="exact").limit(1).execute()
            supabase_ok = not (hasattr(res, "error") and res.error)
        except Exception as e:
            logger.warning(f"⚠️ Supabase health degradado: {type(e).__name__}: {e}")
            supabase_ok = False

        # JWT
        try:
            secret = _jwt_secret()
            jwt_ok = bool(secret and len(secret) >= 16)
        except Exception:
            jwt_ok = False

        # bcrypt
        try:
            test_hash = pwd_ctx.hash("test123")
            bcrypt_ok = pwd_ctx.verify("test123", test_hash)
        except Exception:
            bcrypt_ok = False

        status_txt = "healthy" if (supabase_ok and jwt_ok and bcrypt_ok) else "degraded"
        return {
            "status": status_txt,
            "supabase_connected": supabase_ok,
            "jwt_configured": jwt_ok,
            "bcrypt_working": bcrypt_ok,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "2.1",
        }
    except Exception as e:
        logger.error(f"❌ Auth health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

# ==============================
# Login
# ==============================
@router.post("/login/", response_model=LoginOut, status_code=status.HTTP_200_OK)
async def login(payload: LoginIn, request: Request):
    """
    Endpoint de login:
    - Busca usuario por email (normalizado).
    - Verifica contraseña (bcrypt).
    - Emite JWT con `sub`=user_id y `email`, `name`, `iat`, `exp`, `iss`, `aud`.
    - Devuelve `access_token` + `token_type` + `user`.
    """
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    try:
        # 1) Configuración JWT
        try:
            jwt_secret = _jwt_secret()
        except HTTPException:
            # ya logueado dentro de _jwt_secret
            raise
        except Exception as e:
            logger.error(f"❌ Error configuración JWT: {e}")
            raise HTTPException(status_code=500, detail="Server configuration error: JWT")

        # 2) Buscar usuario (solo columnas reales)
        email_norm = str(payload.email).strip().lower()
        try:
            res = (
                supabase.table("users")
                .select("id,email,hashed_password,name")
                .eq("email", email_norm)
                .limit(1)
                .execute()
            )
        except Exception as supabase_error:
            logger.error(f"❌ Excepción Supabase: {type(supabase_error).__name__}: {supabase_error}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Database connection failed")

        if hasattr(res, "error") and res.error:
            # Supabase devuelve .error en algunos fallos de consulta
            error_msg = str(getattr(res.error, "message", res.error))
            logger.error(f"❌ Error Supabase: {error_msg}")
            raise HTTPException(status_code=500, detail="Database error")

        user_data = getattr(res, "data", None) or []
        if not user_data:
            # 401 para no filtrar existencia
            raise HTTPException(status_code=401, detail="Invalid email or password")

        user_row = user_data[0]
        user_id: str = str(user_row.get("id"))
        user_email: str = str(user_row.get("email"))
        user_name: str | None = user_row.get("name")

        # 3) Verificar contraseña
        password_hash = user_row.get("hashed_password")
        if not password_hash:
            # Usuario mal provisionado: tratar como credenciales inválidas
            logger.warning(f"Usuario sin hashed_password: {email_norm}")
            raise HTTPException(status_code=401, detail="Invalid email or password")

        try:
            if not pwd_ctx.verify(payload.password, password_hash):
                raise HTTPException(status_code=401, detail="Invalid email or password")
        except HTTPException:
            raise
        except Exception as bcrypt_error:
            logger.error(f"❌ Error bcrypt: {type(bcrypt_error).__name__}: {bcrypt_error}")
            raise HTTPException(status_code=500, detail="Password verification failed")

        # 4) Generar JWT
        now_utc = datetime.now(timezone.utc)
        exp_utc = now_utc + timedelta(hours=JWT_TTL_HOURS)
        claims = {
            "sub": user_id,
            "email": user_email,
            "name": user_name,
            "iat": int(now_utc.timestamp()),
            "exp": int(exp_utc.timestamp()),
            "iss": "loyalty-app-backend",
            "aud": "loyalty-app-frontend",
        }

        try:
            token = jwt.encode(claims, jwt_secret, algorithm=JWT_ALG)
        except Exception as jwt_error:
            logger.error(f"❌ Error JWT: {type(jwt_error).__name__}: {jwt_error}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Token generation failed")

        # 5) Respuesta
        return LoginOut(
            access_token=token,
            token_type="bearer",
            user=UserOut(id=user_id, email=user_email, name=user_name),
        )

    except HTTPException as http_ex:
        # Logging conciso y sin datos sensibles
        if http_ex.status_code >= 500:
            logger.error(f"🚫 AUTH {http_ex.status_code}: {http_ex.detail}")
        else:
            logger.info(f"🚫 AUTH {http_ex.status_code}: {http_ex.detail} — IP={client_ip}")
        raise
    except Exception as e:
        logger.error("💥 ERROR CRÍTICO EN LOGIN")
        logger.error(f"💥 {type(e).__name__}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail="Internal server error during authentication",
        )

# ==============================
# Debug (quitar en producción)
# ==============================
@router.get("/debug/users", tags=["debug"])
async def debug_users_list():
    """Lista usuarios (sin contraseñas). Úsalo solo en DEBUG."""
    try:
        res = (
            supabase.table("users")
            .select("id,email,name")
            .limit(5)
            .execute()
        )
        if hasattr(res, "error") and res.error:
            error_msg = str(getattr(res.error, "message", res.error))
            return {"error": error_msg, "supabase_connected": False}

        users_data = getattr(res, "data", []) or []
        return {
            "users_count": len(users_data),
            "sample_users": users_data,
            "table_fields": list(users_data[0].keys()) if users_data else [],
            "supabase_connected": True,
            "debug_timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Error en debug users: {e}")
        return {"error": str(e), "users_count": 0, "supabase_connected": False}

@router.post("/test-jwt", tags=["debug"])
async def test_jwt_generation():
    """Test de generación/verificación de JWT (DEBUG)."""
    try:
        secret = _jwt_secret()
        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": "test-user-123",
                "email": "test@example.com",
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(hours=1)).timestamp()),
            },
            secret,
            algorithm=JWT_ALG,
        )
        decoded = jwt.decode(token, secret, algorithms=[JWT_ALG])
        return {
            "jwt_generation": "success",
            "token_length": len(token),
            "token_preview": f"{token[:20]}...{token[-10:]}",
            "decoded_claims": decoded,
            "secret_length": len(secret),
        }
    except Exception as e:
        return {"jwt_generation": "failed", "error": str(e)}
