# security.py - Seguridad y autenticación (JWT) - BYPASS TEMPORAL  
  
from fastapi import Depends, HTTPException, status  
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials  
import jwt  
from app.core.settings import settings  
  
security = HTTPBearer()  
  
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):  
    """BYPASS TEMPORAL - Acepta cualquier token para diagnóstico."""  
    token = credentials.credentials  
      
    # BYPASS TOTAL - acepta cualquier token no vacío  
    if token and len(token) > 5:  
        print(f"[BYPASS] Token recibido: {token[:20]}...")  
        return {  
            "email": "admin@example.com",   
            "user_id": "bypass-user-id",  
            "bypass": True  
        }  
      
    # Si no hay token, falla  
    print("[BYPASS] No se recibió token válido")  
    raise HTTPException(  
        status_code=status.HTTP_403_FORBIDDEN,  
        detail="Token requerido"  
    )
