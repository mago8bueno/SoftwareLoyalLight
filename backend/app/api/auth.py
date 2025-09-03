# Agregar este endpoint al final de backend/app/api/auth.py

@router.post("/debug-jwt", tags=["debug"])
async def debug_jwt_token(payload: dict):
    """
    Endpoint de debug para diagnosticar problemas JWT.
    Payload: {"token": "jwt_token_here"}
    """
    from app.utils.auth import decode_jwt_debug, test_jwt_secret
    
    try:
        token = payload.get("token", "").strip()
        if not token:
            return {"error": "Token requerido en payload"}
        
        # Info del secreto JWT
        secret_info = test_jwt_secret()
        
        # Decodificar token sin validar firma
        token_info = decode_jwt_debug(token)
        
        # Info de configuración 
        settings_info = {
            "has_jwt_secret": bool(getattr(settings, "JWT_SECRET", None)),
            "has_supabase_key": bool(getattr(settings, "SUPABASE_KEY", None)),
            "jwt_secret_length": len(str(getattr(settings, "JWT_SECRET", ""))) if getattr(settings, "JWT_SECRET", None) else 0,
            "supabase_key_length": len(str(getattr(settings, "SUPABASE_KEY", ""))) if getattr(settings, "SUPABASE_KEY", None) else 0,
        }
        
        return {
            "secret_config": secret_info,
            "token_analysis": token_info, 
            "settings_info": settings_info,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "type": type(e).__name__,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
