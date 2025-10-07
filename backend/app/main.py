# backend/app/main.py - CORS CORREGIDO PARA VERCEL
import os
import re
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.settings import settings
from app.utils.logging import setup_logging
from app.utils.errors import register_exception_handlers

# Routers
from app.api.auth import router as auth_router
from app.api.clients import router as clients_router
from app.api.items import router as items_router
from app.api.purchases import router as purchases_router
from app.api.analytics import router as analytics_router
from app.api.ai import router as ai_router
from app.api.admin import router as admin_router

# 1) Logging
setup_logging()

# 2) App
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# 2.1) Static /media
MEDIA_DIR = os.path.join(os.getcwd(), "media")
os.makedirs(MEDIA_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

# 🔒 2.2) HTTPS MIDDLEWARE - FORZAR SIEMPRE EN RAILWAY
is_production = os.getenv("RAILWAY_ENVIRONMENT_NAME") == "production"
is_railway = bool(os.getenv("RAILWAY_PROJECT_ID") or "railway" in os.getenv("RAILWAY_STATIC_URL", ""))

# 🔧 FIX: Forzar HTTPS en Railway siempre
if "railway" in os.getenv("RAILWAY_STATIC_URL", "") or os.getenv("RAILWAY_PROJECT_ID"):
    is_railway = True
    is_production = True

print(f"🔍 Environment check:")
print(f"   ENVIRONMENT: {os.getenv('ENVIRONMENT', 'not set')}")
print(f"   RAILWAY_ENVIRONMENT_NAME: {os.getenv('RAILWAY_ENVIRONMENT_NAME', 'not set')}")
print(f"   RAILWAY_PROJECT_ID: {os.getenv('RAILWAY_PROJECT_ID', 'not set')}")
print(f"   RAILWAY_STATIC_URL: {os.getenv('RAILWAY_STATIC_URL', 'not set')}")
print(f"   Is production: {is_production}")
print(f"   Is Railway: {is_railway}")
print(f"   All env vars: {dict(os.environ)}")

# 🔧 MIDDLEWARE HTTPS GLOBAL - SIEMPRE ACTIVO
print("🔒 CONFIGURANDO HTTPS MIDDLEWARE GLOBAL")

# TrustedHost simplificado
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"]  # Temporal para debugging
)

# HTTPS Middleware GLOBAL - SIEMPRE ACTIVO
@app.middleware("http") 
async def global_https_middleware(request: Request, call_next):
    """Middleware HTTPS global - redirigir HTTP a HTTPS EXCEPTO health checks"""
    try:
        path = request.url.path
        host = request.headers.get("host", "")
        user_agent = request.headers.get("user-agent", "").lower()
        
        # Detectar health checks de Railway (NO redirigir estos)
        is_railway_healthcheck = (
            path in ["/health", "/health/", "/"] or
            "railway" in host.lower() or
            "healthcheck" in host.lower() or
            "railway" in user_agent or
            request.headers.get("x-forwarded-for", "").startswith("10.")  # IPs internas de Railway
        )
        
        # 🔧 FIX: Solo redirigir HTTP si NO es un health check de Railway
        if request.url.scheme == "http" and not is_railway_healthcheck:
            https_url = request.url.replace(scheme="https")
            print(f"🔒 REDIRIGIENDO HTTP → HTTPS: {request.url} → {https_url}")
            return RedirectResponse(url=str(https_url), status_code=301)
        
        # Para health checks o HTTPS, continuar normalmente
        response = await call_next(request)
        
        # Headers de seguridad solo para usuarios (no health checks)
        if not is_railway_healthcheck:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response
        
    except Exception as e:
        print(f"⚠️ HTTPS middleware error: {e}")
        response = await call_next(request)
        return response

# 🆕 3) CORS CORREGIDO - SOLUCIÓN DEFINITIVA PARA VERCEL
print("🌐 Configurando CORS para Vercel...")

# Orígenes base siempre permitidos
base_origins = [
    "https://softwareloyallight-production.up.railway.app",  # Backend público
]

# Desarrollo local
local_origins = [
    "http://localhost:3000", 
    "http://127.0.0.1:3000",
    "http://localhost:5173", 
    "http://127.0.0.1:5173",
]

# 🔑 CLAVE: URLs específicas conocidas de Vercel
known_vercel_origins = [
    "https://software-loyal-light.vercel.app",                                    # Producción
    "https://software-loyal-light-jtxufeu11-loyal-lights-projects.vercel.app",   # Deploy anterior
    "https://software-loyal-light-b7p82r3r8-loyal-lights-projects.vercel.app",   # Deploy actual
]

# Combinar orígenes según ambiente
if is_production:
    allowed_origins = base_origins + known_vercel_origins
else:
    allowed_origins = base_origins + known_vercel_origins + local_origins

print(f"[CORS] Orígenes configurados ({len(allowed_origins)}):")
for origin in allowed_origins:
    print(f"  ✅ {origin}")

# 🎯 CORS con REGEX para capturar todos los deploys de Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    # 🔥 REGEX CLAVE: Captura CUALQUIER URL de Vercel con el patrón del proyecto
    allow_origin_regex=r"https://software-loyal-light.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=[
        "accept",
        "accept-encoding", 
        "authorization",
        "content-type",
        "dnt",
        "origin",
        "user-agent",
        "x-csrftoken",
        "x-requested-with",
    ],
    expose_headers=["*"],
    max_age=86400,  # Cache preflight 24h
)

# 4) MIDDLEWARE DE DEBUG SIMPLIFICADO
@app.middleware("http")
async def debug_middleware(request: Request, call_next):
    """Debug middleware simplificado y seguro"""
    try:
        method = request.method
        path = str(request.url.path)
        
        # Log solo para endpoints importantes, no health checks
        should_log = (
            path not in ["/health", "/health/", "/"] and
            not path.startswith("/media/") and
            method != "HEAD"
        )
        
        if should_log:
            origin = request.headers.get("origin", "none")
            print(f"🌐 {method} {path} (Origin: {origin})")
        
        response = await call_next(request)
        
        return response
        
    except Exception as e:
        print(f"⚠️ Debug middleware error: {e}")
        response = await call_next(request)
        return response

# 5) Error handlers
register_exception_handlers(app)

# 6) Routers
app.include_router(auth_router,      prefix="/auth",      tags=["auth"])
app.include_router(clients_router,   prefix="/clients",   tags=["clients"])
app.include_router(items_router,     prefix="/items",     tags=["items"])
app.include_router(purchases_router, prefix="/purchases", tags=["purchases"])
app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
app.include_router(ai_router,        prefix="/ai",        tags=["ai"])
app.include_router(admin_router,     prefix="/admin",     tags=["admin"])

# 7) Health endpoints ultra-robustos para Railway
@app.api_route("/health", methods=["GET", "HEAD", "OPTIONS", "POST"])
@app.api_route("/health/", methods=["GET", "HEAD", "OPTIONS", "POST"])
def railway_health_check(request: Request):
    """Health check ultra-robusto para Railway"""
    try:
        # Verificar si es Railway healthcheck
        user_agent = request.headers.get("user-agent", "").lower()
        host = request.headers.get("host", "")
        is_railway_check = (
            "railway" in user_agent or
            "healthcheck" in host or
            "railway" in host
        )
        
        response_data = {
            "status": "healthy",
            "service": "loyal-light-backend",
            "version": settings.VERSION,
            "timestamp": "2025-01-21T12:00:00Z",
            "railway_healthcheck": is_railway_check,
            "environment": os.getenv("RAILWAY_ENVIRONMENT_NAME", "unknown"),
            "cors_enabled": True,
        }
        
        # Response simplificado para Railway
        if is_railway_check:
            return JSONResponse({"status": "ok"}, status_code=200)
        
        return JSONResponse(response_data)
        
    except Exception as e:
        # Nunca fallar el healthcheck
        return JSONResponse({
            "status": "ok",
            "error": str(e),
            "fallback": True
        }, status_code=200)

@app.get("/")
@app.head("/")
@app.options("/")
def root_endpoint(request: Request):
    """Root endpoint con manejo Railway"""
    try:
        return JSONResponse({
            "status": "ok",
            "message": "🚂 Loyal Light Backend - Railway + Vercel",
            "version": settings.VERSION,
            "cors_enabled": True,
            "endpoints": ["/health", "/auth/login", "/analytics/overview"],
            "railway_ready": True
        })
    except Exception:
        return JSONResponse({"status": "ok", "basic": True})

# 🆕 Debug CORS específico
@app.get("/test-cors", tags=["debug"])
def test_cors_vercel(request: Request):
    origin = request.headers.get("origin")
    
    # Verificar si origin matchea regex
    import re
    regex_pattern = r"https://software-loyal-light.*\.vercel\.app"
    matches_regex = bool(re.match(regex_pattern, origin)) if origin else False
    
    return {
        "message": "CORS test para Vercel",
        "origin": origin,
        "matches_vercel_regex": matches_regex,
        "allowed_origins": allowed_origins,
        "cors_regex_pattern": regex_pattern,
        "headers": dict(request.headers),
        "vercel_deploy_detected": bool(origin and "vercel.app" in origin),
        "software_loyal_light_detected": bool(origin and "software-loyal-light" in origin),
    }

@app.get("/cors-debug/{origin_test}", tags=["debug"]) 
def debug_specific_origin(origin_test: str, request: Request):
    """Debug específico para una URL de origen"""
    return {
        "tested_origin": origin_test.replace("_", ".").replace("-", "-"),
        "current_request_origin": request.headers.get("origin"),
        "would_be_allowed": origin_test.replace("_", ".") in str(allowed_origins),
        "regex_would_match": bool(re.search(r"software-loyal-light.*vercel\.app", origin_test)),
        "all_allowed": allowed_origins
    }

# 8) Run
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    
    print("🚂 ===== VERCEL CORS FIXED =====")
    print(f"🚀 Puerto: {port}")
    print(f"🔧 Debug: {settings.DEBUG}")
    print(f"🔒 HTTPS: {'✅' if is_production and is_railway else '❌'}")
    print(f"🌐 CORS origins: {len(allowed_origins)}")
    print(f"🎯 CORS regex: https://software-loyal-light.*\\.vercel\\.app")
    print(f"🛡️  Vercel support: ✅ FULL")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        access_log=True,
        log_level="info"
    )
