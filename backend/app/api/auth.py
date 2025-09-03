# backend/app/api/auth.py - VERSIÓN CORREGIDA (usa solo columnas reales)

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import traceback

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
import jwt

from app.db.supabase import supabase
from app.core.settings import settings

# Logger específico del módulo
logger = logging.getLogger(__name__)

router = APIRouter()

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_ALG = "HS256"
JWT_TTL_HOURS = 24  # caducidad del token

# ==============================
# Utilidades
# ==============================
def _jwt_secret() -> str:
    """Obtiene JWT secret con prioridad JWT_SECRET > SUPABASE_KEY."""
    try:
        if getattr(settings, "JWT_SECRET", None):
            logger.info("✅ Usando JWT_SECRET configurado")
            return str(settings.JWT_SECRET)
        if getattr(settings, "SUPABASE_KEY", None):
            logger.info("⚠️  Usando SUPABASE_KEY como JWT_SECRET fallback")
            return str(settings.SUPABASE_KEY)
        logger.error("❌ No se encontró JWT_SECRET ni SUPABASE_KEY")
        raise ValueError("No JWT secret available")
    except Exception as e:
        logger.error(f"❌ Error obteniendo JWT secret: {e}")
        raise HTTPException(status_code=500, detail="JWT configuration error")

# ==============================
# Schemas
# ==============================
class LoginIn(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: str
    email: str  # usar str para no forzar formato en respuestas
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
    """Health check del servicio de auth."""
    try:
        test_res = supabase.table("users").select("count", count="exact").limit(1).execute()
        supabase_ok = not (hasattr(test_res, "error") and test_res.error)

        # JWT
        try:
            secret = _jwt_secret()
            jwt_ok = bool(secret and len(secret) > 10)
        except Exception:
            jwt_ok = False

        # bcrypt
        try:
            test_hash = pwd_ctx.hash("test123")
            bcrypt_ok = pwd_ctx.verify("test123", test_hash)
        except Exception:
            bcrypt_ok = False

        status = "healthy" if (supabase_ok and jwt_ok and bcrypt_ok) else "degraded"
        return {
            "status": status,
            "supabase_connected": supabase_ok,
            "jwt_configured": jwt_ok,
            "bcrypt_working": bcrypt_ok,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "2.0",
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
@router.post("/login/", response_model=LoginOut)
async def login(payload: LoginIn, request: Request):
    """Endpoint de login con tracing detallado."""
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    try:
        logger.info("=" * 60)
        logger.info(f"🔐 INICIO LOGIN para: {payload.email}")
        logger.info(f"📍 IP: {client_ip}, UA: {user_agent[:80]}")

        # 1) Configuración JWT
        try:
            jwt_secret = _jwt_secret()
            logger.info(f"🔑 JWT Secret length: {len(jwt_secret)}")
        except Exception as e:
            logger.error(f"❌ Error configuración JWT: {e}")
            raise HTTPException(status_code=500, detail="Server configuration error: JWT")

        # 2) Buscar usuario (pedimos SOLO columnas reales)
        email_norm = str(payload.email).lower().strip()
        logger.info(f"🔍 Buscando usuario: {email_norm}")

        try:
            res = (
                supabase.table("users")
                .select("id,email,hashed_password,name")
                .eq("email", email_norm)
                .limit(1)
                .execute()
            )

            if hasattr(res, "error") and res.error:
                error_msg = str(getattr(res.error, "message", res.error))
                logger.error(f"❌ Error Supabase: {error_msg}")
                raise HTTPException(status_code=500, detail=f"Database error: {error_msg}")

            user_data = getattr(res, "data", None) or []
            logger.info(f"👤 Registros obtenidos: {len(user_data)}")

        except HTTPException:
            raise
        except Exception as supabase_error:
            logger.error(f"❌ Excepción Supabase: {type(supabase_error).__name__}: {supabase_error}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Database connection failed: {str(supabase_error)}")

        if not user_data:
            logger.warning(f"⚠️  Usuario NO encontrado: {email_norm}")
            raise HTTPException(status_code=401, detail="Invalid email or password")

        user_row = user_data[0]
        logger.info(f"✅ Usuario encontrado - ID: {user_row.get('id')}")
        logger.info(f"📋 Campos disponibles: {list(user_row.keys())}")

        # 3) Verificar contraseña (usar exclusivamente 'hashed_password')
        password_hash = user_row.get("hashed_password")
        if not password_hash:
            logger.warning(f"Usuario sin hashed_password: {email_norm}")
            # 401 para no exponer si existe o no
            raise HTTPException(status_code=401, detail="Invalid email or password")

        try:
            logger.info("🔐 Verificando contraseña (bcrypt)...")
            password_valid = pwd_ctx.verify(payload.password, password_hash)
            logger.info(f"✅ Contraseña válida: {password_valid}")
        except Exception as bcrypt_error:
            logger.error(f"❌ Error bcrypt: {type(bcrypt_error).__name__}: {bcrypt_error}")
            raise HTTPException(status_code=500, detail="Password verification failed")

        if not password_valid:
            logger.warning(f"⚠️  Contraseña INCORRECTA para: {email_norm}")
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # 4) Preparar token
        user_id = str(user_row["id"])
        user_email = str(user_row["email"])
        user_name = user_row.get("name")

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
            logger.info(f"🎟️ Token emitido (len={len(token)})")
        except Exception as jwt_error:
            logger.error(f"❌ Error JWT: {type(jwt_error).__name__}: {jwt_error}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Token generation failed: {str(jwt_error)}")

        return LoginOut(
            access_token=token,
            token_type="bearer",
            user=UserOut(id=user_id, email=user_email, name=user_name),
        )

    except HTTPException as http_ex:
        logger.error(f"🚫 HTTP Exception: {http_ex.status_code} - {http_ex.detail}")
        raise
    except Exception as e:
        logger.error("💥 ERROR CRÍTICO EN LOGIN")
        logger.error(f"💥 Tipo: {type(e).__name__} | Mensaje: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during authentication: {type(e).__name__}",
        )

# ==============================
# Debug (quitar en producción)
# ==============================
@router.get("/debug/users", tags=["debug"])
async def debug_users_list():
    """Lista usuarios (sin contraseñas)."""
    try:
        res = (
            supabase.table("users")
            .select("id,email,name")  # solo columnas reales y sin password
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
    """Test de generación y verificación de JWT."""
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

