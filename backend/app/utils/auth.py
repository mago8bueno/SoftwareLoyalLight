# backend/app/utils/auth.py
from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
import jwt

from app.core.settings import settings

security = HTTPBearer(auto_error=False)

def _jwt_secret() -> str:
    # Igual que en auth.py: usa JWT_SECRET si existe, si no SUPABASE_KEY
    return (getattr(settings, "JWT_SECRET", None) or settings.SUPABASE_KEY)

def require_user(credentials=Depends(security)) -> str:
    """
    Devuelve el user_id (UUID en texto) extraído del token.
    Lanza 401 si falta/expira/es inválido.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
        user_id = payload.get("sub")  # 👈 en tu token el id va en "sub"
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
