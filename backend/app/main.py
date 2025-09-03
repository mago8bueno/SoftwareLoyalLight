# backend/app/main.py - AÑADIR ESTE ENDPOINT TEMPORAL
# Añadir antes de las líneas finales del archivo main.py

@app.get("/debug/railway", tags=["debug"])
def railway_diagnostics():
    """🔧 DIAGNÓSTICO COMPLETO RAILWAY - Remover en producción"""
    import os
    import socket
    from urllib.parse import urlparse
    
    try:
        # 1. Variables de entorno críticas
        env_status = {
            "SUPABASE_URL": bool(os.getenv("SUPABASE_URL")),
            "SUPABASE_KEY": bool(os.getenv("SUPABASE_KEY")),
            "JWT_SECRET": bool(os.getenv("JWT_SECRET")),
            "PORT": os.getenv("PORT", "not_set"),
            "RAILWAY_ENVIRONMENT": os.getenv("RAILWAY_ENVIRONMENT", "not_railway"),
        }
        
        # 2. Test de conectividad a Supabase
        supabase_url = os.getenv("SUPABASE_URL", "")
        connectivity_test = {"supabase_reachable": False, "error": None}
        
        if supabase_url:
            try:
                parsed_url = urlparse(supabase_url)
                host = parsed_url.hostname
                port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
                
                # Test de socket (timeout 10 segundos)
                sock = socket.create_connection((host, port), timeout=10)
                sock.close()
                connectivity_test["supabase_reachable"] = True
                
            except Exception as e:
                connectivity_test["error"] = str(e)
        
        # 3. Test de Supabase client
        supabase_client_test = {"initialized": False, "query_works": False, "error": None}
        
        try:
            from app.db.supabase import supabase
            supabase_client_test["initialized"] = True
            
            # Test query básica
            result = supabase.table("auth").select("count", count="exact").limit(1).execute()
            
            if not (hasattr(result, 'error') and result.error):
                supabase_client_test["query_works"] = True
            else:
                supabase_client_test["error"] = str(result.error)
                
        except Exception as e:
            supabase_client_test["error"] = str(e)
        
        # 4. Test JWT
        jwt_test = {"secret_available": False, "can_generate": False, "error": None}
        
        try:
            from app.utils.auth import _jwt_secret
            import jwt as pyjwt
            from datetime import datetime, timedelta, timezone
            
            secret = _jwt_secret()
            jwt_test["secret_available"] = bool(secret and len(secret) > 10)
            
            if jwt_test["secret_available"]:
                # Test de generación JWT
                test_token = pyjwt.encode({
                    "sub": "test",
                    "exp": datetime.now(timezone.utc) + timedelta(hours=1)
                }, secret, algorithm="HS256")
                
                # Test de decodificación
                decoded = pyjwt.decode(test_token, secret, algorithms=["HS256"])
                jwt_test["can_generate"] = bool(decoded.get("sub") == "test")
                
        except Exception as e:
            jwt_test["error"] = str(e)
        
        # 5. Información del sistema
        system_info = {
            "python_version": os.sys.version,
            "railway_region": os.getenv("RAILWAY_REGION", "unknown"),
            "railway_replica_id": os.getenv("RAILWAY_REPLICA_ID", "unknown"),
            "hostname": socket.gethostname(),
        }
        
        # 6. Status general
        all_critical_ok = (
            env_status["SUPABASE_URL"] and 
            env_status["SUPABASE_KEY"] and 
            env_status["JWT_SECRET"] and
            connectivity_test["supabase_reachable"] and
            supabase_client_test["query_works"] and
            jwt_test["can_generate"]
        )
        
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "🟢 HEALTHY" if all_critical_ok else "🔴 ISSUES_FOUND",
            "environment_vars": env_status,
            "connectivity": connectivity_test,
            "supabase_client": supabase_client_test,
            "jwt_system": jwt_test,
            "system_info": system_info,
            "recommendations": [
                "✅ Configurar SUPABASE_URL en Railway" if not env_status["SUPABASE_URL"] else None,
                "✅ Configurar SUPABASE_KEY en Railway" if not env_status["SUPABASE_KEY"] else None,
                "✅ Configurar JWT_SECRET en Railway" if not env_status["JWT_SECRET"] else None,
                "✅ Verificar conectividad de red" if not connectivity_test["supabase_reachable"] else None,
                "✅ Verificar configuración Supabase" if not supabase_client_test["query_works"] else None,
            ],
            "next_steps": [
                "1. Configurar variables de entorno en Railway Dashboard",
                "2. Hacer redeploy del servicio",
                "3. Esperar 2-3 minutos para propagación",
                "4. Probar endpoint /auth/health",
                "5. Probar login con admin@example.com / admin123"
            ] if not all_critical_ok else [
                "🎉 ¡Todo configurado correctamente!",
                "🔗 Probar login en tu frontend",
                "🗑️  Remover endpoints /debug/* en producción"
            ]
        }
        
    except Exception as e:
        return {
            "status": "🔴 CRITICAL_ERROR",
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.now().isoformat()
        }
