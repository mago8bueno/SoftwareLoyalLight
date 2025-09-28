# backend/app/main.py - CORS CORREGIDO PARA VERCEL
import os
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

# 🔒 2.2) HTTPS MIDDLEWARE
is_production = os.getenv("RAILWAY_ENVIRONMENT_NAME") == "production"
is_railway = bool(os.getenv("RAILWAY_PROJECT_ID") or "railway" in os.getenv("RAILWAY_STATIC_URL", ""))

print(f"🔍 Environment check:")
print(f"   ENVIRONMENT: {os.getenv('ENVIRONMENT', 'not set')}")
print(f"   RAILWAY_ENVIRONMENT_NAME: {os.getenv('RAILWAY_ENVIRONMENT_NAME', 'not set')}")
print(f"   RAILWAY_PROJECT_ID: {bool(os.getenv('RAILWAY_PROJECT_ID'))}")
print(f"   Is production: {is_production}")
print(f"   Is Railway: {is_railway}")

if is_production and is_railway:
    print("🔒 HABILITANDO HTTPS REDIRECT EN PRODUCCIÓN RAILWAY")
    
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=[
            "softwareloyallight-production.up.railway.app",
            "*.up.railway.app",
            "*.vercel.app", 
            "localhost",
            "127.0.0.1",
        ]
    )

    # Middleware para forzar HTTPS (optimizado para Railway health checks)
    @app.middleware("http")
    async def force_https_redirect(request: Request, call_next):
        forwarded_proto = request.headers.get("x-forwarded-proto")
        host = request.headers.get("host", "")
        path = request.url.path
        
        # Excepciones para health checks de Railway
        is_railway_healthcheck = (
            host == "healthcheck.railway.app" or 
            path in ["/health", "/health/", "/"] or
            "railway" in host
        )
        
        # Solo redirigir HTTP→HTTPS para requests de usuarios, no health checks
        should_redirect = (
            not is_railway_healthcheck and
            (forwarded_proto == "http" or (not forwarded_proto and request.url.scheme == "http"))
        )
        
        if should_redirect:
            https_url = request.url.replace(scheme="https")
            print(f"🔄 HTTP → HTTPS redirect: {request.url} → {https_url}")
            return RedirectResponse(url=str(https_url), status_code=301)
        
        response = await call_next(request)
        
        # Añadir headers de seguridad solo para requests de usuarios
        if not is_railway_healthcheck:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
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

# 4) MIDDLEWARE DE DEBUG MEJORADO
@app.middleware("http")
async def enhanced_debug_middleware(request: Request, call_next):
    """Enhanced debugging para CORS y auth"""
    origin = request.headers.get("origin")
    method = request.method
    path = str(request.url.path)
    
    # Log CORS requests
    if method == "OPTIONS":
        print(f"🔄 PREFLIGHT: {method} {path}")
        print(f"   Origin: {origin}")
        print(f"   Headers: {dict(request.headers)}")
    
    # Log important endpoints
    if any(endpoint in path for endpoint in ["/auth/", "/analytics/", "/ai/"]):
        auth_header = request.headers.get("authorization", "")
        print(f"🌐 {method} {path}")
        print(f"   Origin: {origin}")
        print(f"   Has Auth: {bool(auth_header)}")
        if auth_header and len(auth_header) > 20:
            print(f"   Auth Preview: {auth_header[:20]}...")
    
    response = await call_next(request)
    
    # Log respuestas de CORS
    if method == "OPTIONS":
        print(f"📤 PREFLIGHT Response: {response.status_code}")
        cors_headers = {k: v for k, v in response.headers.items() if 'access-control' in k.lower()}
        print(f"   CORS Headers: {cors_headers}")
    
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

# 7) Health endpoints mejorados
def _health_response():
    return JSONResponse({
        "status": "ok", 
        "version": settings.VERSION,
        "https_enabled": is_production and is_railway,
        "cors_enabled": True,
        "cors_origins": len(allowed_origins),
        "cors_regex": "https://software-loyal-light.*\\.vercel\\.app",
        "environment": os.getenv("RAILWAY_ENVIRONMENT_NAME", "development"),
        "railway_project": bool(os.getenv("RAILWAY_PROJECT_ID")),
        "server": "Railway",
        "timestamp": "2025-01-21T12:00:00Z",
        "message": f"🚂 Backend Railway + Vercel CORS ({'HTTPS' if is_production else 'HTTP'})"
    })

@app.get("/")
@app.head("/")
@app.options("/")
def root():
    return _health_response()

@app.api_route("/health", methods=["GET", "HEAD", "OPTIONS"])
@app.api_route("/health/", methods=["GET", "HEAD", "OPTIONS"])
def health_check():
    return _health_response()

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
