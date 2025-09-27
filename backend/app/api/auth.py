# app/utils/auth.py
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
import os

try:
    import jwt  # PyJWT
except Exception:  # pragma: no cover
    jwt = None

try:
    from passlib.hash import bcrypt
except Exception:  # pragma: no cover
    bcrypt = None

from app.core.settings import settings

ALGORITHM = "HS256"

def _get_secret() -> str:
    # Prioriza settings, luego env, luego fallback inseguro (solo para dev)
    return getattr(settings, "JWT_SECRET", None) or os.getenv("JWT_SECRET", "dev-insecure-secret")

def create_jwt_token(payload: Dict[str, Any], expires_minutes: int = 60 * 24) -> str:
    """
    Crea un JWT HS256 con 'exp' e 'iat'.
    """
    if jwt is None:
        raise RuntimeError("PyJWT no instalado. Añade 'PyJWT' a requirements.")
    now = datetime.now(timezone.utc)
    to_encode = {
        **payload,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    token = jwt.encode(to_encode, _get_secret(), algorithm=ALGORITHM)
    # PyJWT>=2 devuelve str, en versiones antiguas bytes
    return token if isinstance(token, str) else token.decode("utf-8")

def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Verifica contraseña:
      - Si el hash parece bcrypt ($2...) y passlib está disponible -> bcrypt.verify
      - Si no, hace comparación directa (solo útil en dev si guardaste en texto claro)
    """
    if not stored_hash:
        return False
    # Heurística de bcrypt
    is_bcrypt = stored_hash.startswith("$2a$") or stored_hash.startswith("$2b$") or stored_hash.startswith("$2y$")
    if is_bcrypt and bcrypt is not None:
        try:
            return bcrypt.verify(plain_password, stored_hash)
        except Exception:
            return False
    # Fallback (no recomendado en producción)
    return plain_password == stored_hash

def decode_jwt_debug(token: str) -> Dict[str, Any]:
    """
    Decodifica SIN validar firma/exp para debug.
    """
    if jwt is None:
        raise RuntimeError("PyJWT no instalado. Añade 'PyJWT' a requirements.")
    try:
        header = jwt.get_unverified_header(token)
    except Exception as e:
        header = {"error": f"header inválido: {e.__class__.__name__}: {e}"}
    try:
        payload = jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
    except Exception as e:
        payload = {"error": f"payload inválido: {e.__class__.__name__}: {e}"}
    return {"header": header, "payload": payload}

def test_jwt_secret() -> Dict[str, Any]:
    """
    Devuelve info diagnóstica del secreto JWT (sin exponerlo).
    """
    secret = _get_secret()
    return {
        "configured": bool(secret),
        "length": len(secret or ""),
        "preview": (secret[:2] + "***" + secret[-2:]) if secret and len(secret) >= 4 else "***",
        "algorithm": ALGORITHM,
    }
