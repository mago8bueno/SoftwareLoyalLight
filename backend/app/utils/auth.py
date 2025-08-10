# backend/app/utils/auth.py
from __future__ import annotations

from fastapi import Header, HTTPException, status
import jwt

from app.core.settings import settings

JWT_ALG = "HS256"

def _jwt_secret() -> str:
    return (getattr(settings, "JWT_SECRET", None) or settings.SUPABASE_KEY)


def require_user(authorization: str | None = Header(None, alias="Authorization")) -> dict:
    """
    Extrae y valida el JWT de Authorization: Bearer <token>.
    Devuelve {id, email} del usuario autenticado.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    token = authorization.split(" ", 1)[1].strip()

    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    email = payload.get("email")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return {"id": user_id, "email": email}
