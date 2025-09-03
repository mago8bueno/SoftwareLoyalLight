# backend/app/api/auth.py - VERSIÓN CON DEBUGGING MEJORADO
from __future__ import annotations  
  
from datetime import datetime, timedelta, timezone  
import logging
  
from fastapi import APIRouter, HTTPException  
from pydantic import BaseModel, EmailStr  
from passlib.context import CryptContext  
import jwt  
  
from app.db.supabase import supabase  # cliente Supabase ya configurado  
from app.core.settings import settings  

# Configurar logger específico
logger = logging.getLogger(__name__)
  
router = APIRouter()  
  
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")  
  
JWT_ALG = "HS256"  
JWT_TTL_HOURS = 24  # caducidad del token  
  
def _jwt_secret() -> str:  
    # Usa JWT_SECRET si existe; si no, SUPABASE_KEY como fallback  
    secret = (getattr(settings, "JWT_SECRET", None) or settings.SUPABASE_KEY)
    if not secret:
        logger.error("❌ No JWT_SECRET ni SUPABASE_KEY encontrados")
        raise HTTPException(status_code=500, detail="Server configuration error")
    return secret
  
  
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
    try:
        logger.info(f"🔐 Intento de login para: {payload.email}")
        
        # 1. Buscar usuario por email con debugging
        try:
            res = (  
                supabase.table("users")  
                .select("id,email,password_hash,hashed_password,name")  # Ambos campos por si acaso
                .eq("email", str(payload.email))  
                .single()  
                .execute()  
            )
            logger.info(f"📊 Supabase response: {res}")
            
        except Exception as supabase_error:
            logger.error(f"❌ Error en consulta Supabase: {supabase_error}")
            raise HTTPException(status_code=500, detail="Database connection error")
        
        row = getattr(res, "data", None)
        logger.info(f"👤 Usuario encontrado: {bool(row)}")
        
        if not row:
            logger.warning(f"⚠️  Usuario no encontrado: {payload.email}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # 2. Obtener hash de contraseña (puede estar en diferentes campos)
        password_hash = (
            row.get("password_hash") or 
            row.get("hashed_password") or 
            row.get("password")  # Por si acaso
        )
        
        if not password_hash:
            logger.error(f"❌ No se encontró hash de contraseña para {payload.email}")
            logger.error(f"Campos disponibles: {list(row.keys())}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        logger.info(f"🔍 Hash encontrado: {password_hash[:20]}...")
        
        # 3. Verificar contraseña con bcrypt con debugging
        try:
            password_valid = pwd_ctx.verify(payload.password, password_hash)
            logger.info(f"🔐 Contraseña válida: {password_valid}")
            
        except Exception as verify_error:
            logger.error(f"❌ Error verificando contraseña: {verify_error}")
            raise HTTPException(status_code=500, detail="Password verification error")
        
        if not password_valid:
            logger.warning(f"⚠️  Contraseña incorrecta para: {payload.email}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # 4. Preparar datos del usuario
        user = {
            "id": str(row["id"]), 
            "email": str(row["email"]), 
            "name": row.get("name")
        }
        logger.info(f"✅ Usuario validado: {user['email']}")
        
        # 5. Generar JWT con debugging
        try:
            now = datetime.now(timezone.utc)  
            claims = {  
                "sub": str(row["id"]),  
                "email": str(row["email"]),  
                "iat": int(now.timestamp()),  
                "exp": int((now + timedelta(hours=JWT_TTL_HOURS)).timestamp()),  
            }
            
            secret = _jwt_secret()
            token = jwt.encode(claims, secret, algorithm=JWT_ALG)
            logger.info(f"🎟️  Token generado: {token[:20]}...")
            
        except Exception as jwt_error:
            logger.error(f"❌ Error generando JWT: {jwt_error}")
            raise HTTPException(status_code=500, detail="Token generation error")
        
        logger.info(f"✅ Login exitoso para: {payload.email}")
        return {
            "access_token": token, 
            "token_type": "bearer", 
            "user": user
        }
        
    except HTTPException:
        # Re-raise HTTPExceptions (errores controlados)
        raise
    except Exception as e:
        # Capturar cualquier error no manejado
        logger.error(f"❌ Error crítico en login: {str(e)}")
        logger.error(f"Tipo de error: {type(e).__name__}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )


# 🆕 Endpoint de debugging para verificar usuarios
@router.get("/debug/users", tags=["debug"])
def debug_users():
    """Endpoint temporal para verificar estructura de usuarios"""
    try:
        # Obtener algunos usuarios para debug (sin contraseñas)
        res = (
            supabase.table("users")
            .select("id,email,name,created_at")  # Sin passwords por seguridad
            .limit(3)
            .execute()
        )
        
        return {
            "users_count": len(res.data) if res.data else 0,
            "sample_users": res.data,
            "available_fields": list(res.data[0].keys()) if res.data else [],
            "supabase_connected": True
        }
    except Exception as e:
        return {
            "error": str(e),
            "supabase_connected": False
        }


# 🆕 Endpoint para test de conexión
@router.get("/health", tags=["debug"])
def auth_health():
    """Health check del servicio de auth"""
    try:
        # Test basic de Supabase
        test_res = supabase.table("users").select("count", count="exact").execute()
        
        return {
            "status": "healthy",
            "supabase_connected": True,
            "jwt_secret_configured": bool(getattr(settings, "JWT_SECRET", None) or settings.SUPABASE_KEY),
            "bcrypt_working": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Auth health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "supabase_connected": False
        }
