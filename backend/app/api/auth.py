# backend/app/api/auth.py - VERSIÓN COMPLETAMENTE CORREGIDA
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

# Configurar logger específico
logger = logging.getLogger(__name__)
  
router = APIRouter()  
  
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")  
  
JWT_ALG = "HS256"  
JWT_TTL_HOURS = 24  # caducidad del token  

# ✅ CORREGIR: Función de JWT secret más robusta
def _jwt_secret() -> str:  
    """Obtiene JWT secret de forma robusta"""
    try:
        # Prioridad: JWT_SECRET > SUPABASE_KEY 
        if hasattr(settings, "JWT_SECRET") and settings.JWT_SECRET:
            logger.info("✅ Usando JWT_SECRET configurado")
            return str(settings.JWT_SECRET)
        elif hasattr(settings, "SUPABASE_KEY") and settings.SUPABASE_KEY:
            logger.info("⚠️  Usando SUPABASE_KEY como JWT_SECRET fallback")
            return str(settings.SUPABASE_KEY)
        else:
            logger.error("❌ No se encontró JWT_SECRET ni SUPABASE_KEY")
            raise ValueError("No JWT secret available")
    except Exception as e:
        logger.error(f"❌ Error obteniendo JWT secret: {e}")
        raise HTTPException(status_code=500, detail="JWT configuration error")

class LoginIn(BaseModel):  
    email: EmailStr  
    password: str  

class UserOut(BaseModel):  
    id: str  
    email: str  # ✅ CORREGIR: usar str en lugar de EmailStr 
    name: str | None = None  

class LoginOut(BaseModel):  
    access_token: str  
    token_type: str = "bearer"  
    user: UserOut  

# ✅ AÑADIR: Health check endpoint
@router.get("/health", tags=["auth", "debug"])
def auth_health_check():
    """Health check mejorado del servicio de auth"""
    try:
        # Test de conexión Supabase
        test_res = supabase.table("users").select("count", count="exact").limit(1).execute()
        supabase_ok = not (hasattr(test_res, 'error') and test_res.error)
        
        # Test JWT secret
        jwt_ok = True
        try:
            secret = _jwt_secret()
            jwt_ok = bool(secret and len(secret) > 10)
        except Exception:
            jwt_ok = False
        
        # Test bcrypt
        bcrypt_ok = True
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
            "version": "2.0"
        }
    except Exception as e:
        logger.error(f"❌ Auth health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# ✅ CORREGIR: Login endpoint completamente reescrito
@router.post("/login/", response_model=LoginOut)  
async def login(payload: LoginIn, request: Request):
    """Login endpoint completamente corregido con debugging exhaustivo"""
    
    # Headers de debug
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    try:
        logger.info("=" * 60)
        logger.info(f"🔐 INICIO LOGIN para: {payload.email}")
        logger.info(f"📍 IP: {client_ip}, User-Agent: {user_agent[:50]}...")
        
        # ✅ 1. VERIFICAR CONFIGURACIÓN INICIAL
        try:
            jwt_secret = _jwt_secret()
            logger.info(f"🔑 JWT Secret configurado: {len(jwt_secret)} caracteres")
        except Exception as e:
            logger.error(f"❌ Error configuración JWT: {e}")
            raise HTTPException(status_code=500, detail="Server configuration error: JWT")
        
        # ✅ 2. BUSCAR USUARIO CON MANEJO ROBUSTO
        logger.info(f"🔍 Buscando usuario: {payload.email}")
        
        try:
            # Query más específica y con timeout
            user_query = (  
                supabase.table("users")  
                .select("id,email,password_hash,hashed_password,name,role,created_at")
                .eq("email", str(payload.email).lower().strip())  # normalizar email
                .limit(1)
            )
            
            logger.info(f"📊 Ejecutando query Supabase...")
            res = user_query.execute()
            
            # Debug detallado de respuesta Supabase
            logger.info(f"📈 Supabase response type: {type(res)}")
            logger.info(f"📈 Supabase response attrs: {dir(res)}")
            
            if hasattr(res, 'error') and res.error:
                error_msg = str(getattr(res.error, 'message', res.error))
                logger.error(f"❌ Error Supabase: {error_msg}")
                raise HTTPException(status_code=500, detail=f"Database error: {error_msg}")
            
            user_data = getattr(res, "data", None)
            logger.info(f"👤 Datos usuario raw: {type(user_data)} - {len(user_data) if user_data else 0} registros")
            
        except HTTPException:
            raise  # Re-lanzar HTTPExceptions
        except Exception as supabase_error:
            logger.error(f"❌ Excepción Supabase: {type(supabase_error).__name__}: {supabase_error}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Database connection failed: {str(supabase_error)}")
        
        # ✅ 3. VALIDAR USUARIO ENCONTRADO
        if not user_data or len(user_data) == 0:
            logger.warning(f"⚠️  Usuario NO encontrado: {payload.email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        user_row = user_data[0]  # Tomar primer registro
        logger.info(f"✅ Usuario encontrado - ID: {user_row.get('id')}")
        logger.info(f"📋 Campos disponibles: {list(user_row.keys())}")
        
        # ✅ 4. OBTENER HASH DE CONTRASEÑA
        password_hash = (
            user_row.get("password_hash") or 
            user_row.get("hashed_password") or 
            user_row.get("password")
        )
        
        if not password_hash:
            logger.error(f"❌ Sin hash de contraseña para {payload.email}")
            logger.error(f"❌ Campos user_row: {user_row}")
            raise HTTPException(status_code=500, detail="User password not properly configured")
        
        logger.info(f"🔍 Password hash encontrado: {password_hash[:30]}...")
        
        # ✅ 5. VERIFICAR CONTRASEÑA CON BCRYPT
        try:
            logger.info(f"🔐 Verificando contraseña con bcrypt...")
            password_valid = pwd_ctx.verify(payload.password, password_hash)
            logger.info(f"✅ Contraseña válida: {password_valid}")
            
        except Exception as bcrypt_error:
            logger.error(f"❌ Error bcrypt: {type(bcrypt_error).__name__}: {bcrypt_error}")
            raise HTTPException(status_code=500, detail="Password verification failed")
        
        if not password_valid:
            logger.warning(f"⚠️  Contraseña INCORRECTA para: {payload.email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # ✅ 6. PREPARAR DATOS DE USUARIO
        user_id = str(user_row["id"])
        user_email = str(user_row["email"])
        user_name = user_row.get("name")
        
        logger.info(f"✅ Datos usuario validados - ID: {user_id}, Email: {user_email}")
        
        # ✅ 7. GENERAR TOKEN JWT
        try:
            logger.info(f"🎟️  Generando JWT token...")
            
            now_utc = datetime.now(timezone.utc)
            exp_utc = now_utc + timedelta(hours=JWT_TTL_HOURS)
            
            jwt_claims = {  
                "sub": user_id,  # subject = user_id
                "email": user_email,  
                "name": user_name,
                "iat": int(now_utc.timestamp()),  
                "exp": int(exp_utc.timestamp()),
                "iss": "loyalty-app-backend",  # issuer
                "aud": "loyalty-app-frontend",  # audience
            }
            
            logger.info(f"🏷️  JWT claims: {jwt_claims}")
            
            # Generar token
            token = jwt.encode(jwt_claims, jwt_secret, algorithm=JWT_ALG)
            logger.info(f"🎟️  Token generado: {token[:50]}...")
            
        except Exception as jwt_error:
            logger.error(f"❌ Error JWT: {type(jwt_error).__name__}: {jwt_error}")
            logger.error(f"❌ JWT Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Token generation failed: {str(jwt_error)}")
        
        # ✅ 8. PREPARAR RESPUESTA FINAL
        user_response = UserOut(
            id=user_id,
            email=user_email, 
            name=user_name
        )
        
        login_response = LoginOut(
            access_token=token, 
            token_type="bearer", 
            user=user_response
        )
        
        logger.info(f"🎉 LOGIN EXITOSO para: {payload.email}")
        logger.info(f"🎟️  Token size: {len(token)} chars")
        logger.info("=" * 60)
        
        return login_response
        
    except HTTPException as http_ex:
        # Re-lanzar HTTPExceptions sin modificar
        logger.error(f"🚫 HTTP Exception: {http_ex.status_code} - {http_ex.detail}")
        raise http_ex
        
    except Exception as e:
        # Capturar errores inesperados
        logger.error(f"💥 ERROR CRÍTICO EN LOGIN:")
        logger.error(f"💥 Tipo: {type(e).__name__}")
        logger.error(f"💥 Mensaje: {str(e)}")
        logger.error(f"💥 Traceback completo:\n{traceback.format_exc()}")
        logger.error("=" * 60)
        
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error during authentication: {type(e).__name__}"
        )

# ✅ AÑADIR: Endpoint de debug temporal para verificar usuarios
@router.get("/debug/users", tags=["debug"])
async def debug_users_list():
    """🔧 DEBUG: Lista usuarios sin contraseñas (REMOVER EN PRODUCCIÓN)"""
    try:
        logger.info("🔍 Debug: Listando usuarios...")
        
        res = (
            supabase.table("users")
            .select("id,email,name,role,created_at")  # SIN passwords por seguridad
            .limit(5)
            .execute()
        )
        
        if hasattr(res, 'error') and res.error:
            error_msg = str(getattr(res.error, 'message', res.error))
            return {"error": error_msg, "supabase_connected": False}
        
        users_data = getattr(res, 'data', []) or []
        
        return {
            "users_count": len(users_data),
            "sample_users": users_data,
            "table_fields": list(users_data[0].keys()) if users_data else [],
            "supabase_connected": True,
            "debug_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error en debug users: {e}")
        return {
            "error": str(e),
            "users_count": 0,
            "supabase_connected": False
        }

# ✅ AÑADIR: Test JWT endpoint
@router.post("/test-jwt", tags=["debug"])
async def test_jwt_generation():
    """🔧 DEBUG: Test generación JWT"""
    try:
        secret = _jwt_secret()
        
        test_claims = {
            "sub": "test-user-123",
            "email": "test@example.com",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        }
        
        token = jwt.encode(test_claims, secret, algorithm=JWT_ALG)
        
        # Verificar decodificación
        decoded = jwt.decode(token, secret, algorithms=[JWT_ALG])
        
        return {
            "jwt_generation": "success",
            "token_length": len(token),
            "token_preview": f"{token[:20]}...{token[-10:]}",
            "decoded_claims": decoded,
            "secret_length": len(secret)
        }
        
    except Exception as e:
        return {
            "jwt_generation": "failed", 
            "error": str(e)
        }
