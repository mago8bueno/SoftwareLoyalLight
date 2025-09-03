# backend/app/utils/auth.py — VERSIÓN CORREGIDA JWT + DEBUG
from __future__ import annotations

import logging
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
import jwt

from app.core.settings import settings

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

def _jwt_secret() -> str:
    """
    Obtiene el secreto JWT con fallback robusto.
    Prioridad: JWT_SECRET -> SUPABASE_KEY
    """
    # Prioridad 1: JWT_SECRET específico
    if hasattr(settings, "JWT_SECRET") and settings.JWT_SECRET:
        secret = str(settings.JWT_SECRET)
        if len(secret) >= 16:  # Mínimo de seguridad
            return secret
    
    # Prioridad 2: Fallback a SUPABASE_KEY
    if hasattr(settings, "SUPABASE_KEY") and settings.SUPABASE_KEY:
        secret = str(settings.SUPABASE_KEY)
        if len(secret) >= 16:
            logger.warning("⚠️  Usando SUPABASE_KEY como JWT secret (fallback)")
            return secret
    
    # Error: No hay secreto válido
    logger.error("❌ No se encontró JWT_SECRET válido")
    raise HTTPException(
        status_code=500, 
        detail="JWT configuration error"
    )

def require_user(credentials=Depends(security)) -> str:
    """
    Extrae y valida el JWT token, devuelve user_id.
    
    - Valida formato Bearer
    - Decodifica JWT con el secreto correcto
    - Verifica expiración y firma
    - Extrae user_id del claim 'sub'
    """
    
    # 1. Verificar que hay credentials
    if not credentials or not credentials.credentials:
        logger.info("🚫 Auth: Missing Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    
    # 2. Verificar formato del token
    if not token or len(token) < 50:  # JWT mínimo son ~100 chars
        logger.info(f"🚫 Auth: Token too short: {len(token)} chars")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # 3. Obtener secreto JWT
        try:
            jwt_secret = _jwt_secret()
        except HTTPException:
            raise  # Ya logueado en _jwt_secret()
        except Exception as e:
            logger.error(f"❌ Error getting JWT secret: {e}")
            raise HTTPException(status_code=500, detail="Server configuration error")

        # 4. Debug info (solo primeros/últimos chars por seguridad)
        token_preview = f"{token[:20]}...{token[-10:]}"
        secret_preview = f"{jwt_secret[:8]}{'*' * (len(jwt_secret) - 16)}{jwt_secret[-8:]}"
        
        logger.info(f"🔍 JWT Validation:")
        logger.info(f"   Token: {token_preview} (len: {len(token)})")
        logger.info(f"   Secret: {secret_preview} (len: {len(jwt_secret)})")

        # 5. Decodificar JWT
        try:
            payload = jwt.decode(
                token, 
                jwt_secret, 
                algorithms=["HS256"],
                # Opciones de verificación
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True, 
                    "verify_iss": False,  # No verificar issuer por ahora
                    "verify_aud": False,  # No verificar audience por ahora
                }
            )
            
        except jwt.ExpiredSignatureError:
            logger.info("🚫 Auth: Token expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired", 
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidSignatureError:
            logger.error("🚫 Auth: Invalid token signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token signature",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.DecodeError as e:
            logger.error(f"🚫 Auth: Token decode error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            logger.error(f"🚫 Auth: Invalid token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 6. Extraer user_id del claim 'sub'
        user_id = payload.get("sub")
        if not user_id:
            logger.error(f"🚫 Auth: Missing 'sub' claim in token. Payload: {list(payload.keys())}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload - missing user ID",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 7. Validar que user_id sea string válido
        user_id = str(user_id).strip()
        if not user_id or len(user_id) < 10:  # UUID mínimo son 36 chars
            logger.error(f"🚫 Auth: Invalid user_id format: '{user_id}'")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID in token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 8. Log success (sin datos sensibles)
        email = payload.get("email", "unknown")
        exp = payload.get("exp", 0)
        exp_time = datetime.fromtimestamp(exp, tz=timezone.utc) if exp else "unknown"
        
        logger.info(f"✅ Auth success: user_id={user_id[:8]}...{user_id[-4:]} email={email} exp={exp_time}")
        
        return user_id

    except HTTPException:
        # Re-lanzar HTTPExceptions tal como están
        raise
    except Exception as e:
        # Cualquier otra excepción inesperada
        logger.error(f"❌ Unexpected auth error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )

# ===== UTILITIES DE DEBUG =====

def decode_jwt_debug(token: str) -> dict:
    """
    Función de debug para decodificar JWT sin validación.
    ¡SOLO PARA DEBUG - NO USAR EN PRODUCCIÓN!
    """
    try:
        # Decodificar sin verificar firma (solo para debug)
        payload = jwt.decode(token, options={"verify_signature": False})
        return {
            "valid_format": True,
            "payload": payload,
            "claims": list(payload.keys()),
            "sub": payload.get("sub"),
            "email": payload.get("email"), 
            "exp": payload.get("exp"),
            "iat": payload.get("iat"),
        }
    except Exception as e:
        return {
            "valid_format": False,
            "error": str(e),
            "token_length": len(token),
            "token_preview": f"{token[:20]}...{token[-10:]}" if len(token) > 30 else token
        }

def test_jwt_secret() -> dict:
    """
    Función de debug para probar la configuración JWT.
    """
    try:
        secret = _jwt_secret()
        return {
            "secret_configured": True,
            "secret_length": len(secret),
            "secret_preview": f"{secret[:8]}{'*' * max(0, len(secret) - 16)}{secret[-8:] if len(secret) > 16 else ''}",
            "source": "JWT_SECRET" if hasattr(settings, "JWT_SECRET") and settings.JWT_SECRET else "SUPABASE_KEY"
        }
    except Exception as e:
        return {
            "secret_configured": False,
            "error": str(e)
        }
