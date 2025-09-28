# backend/app/main.py - VERSIÓN CORREGIDA TRUSTEDHOST
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

# 🔒 2.2) HTTPS MIDDLEWARE - DETECCIÓN MEJORADA
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
    
    # ✅ CORREGIDO: TrustedHostMiddleware con patrones válidos
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=[
            "softwareloyallight-production.up.railway.app",
            "*.up.railway.app",  # ✅ Formato correcto para wildcard
            "software-loyal-light.vercel.app",
            "*.vercel.app",      # ✅ Formato correcto para wildcard
            "localhost",
            "127.0.0.1",
            "*",                 # ✅ Solo en desarrollo/debug
        ] if settings.DEBUG else [
            # Solo dominios específicos en producción
            "softwareloyallight-production.up.railway.app",
            "software-loyal-light.vercel.app",
            "software-loyal-light-jtxufeu11-loyal-lights-projects.vercel.app",
        ]
    )

    # Middleware para forzar HTTPS
    @app.middleware("http")
    async def force_https_redirect(request: Request, call_next):
        """Fuerza HTTPS redirect en Railway production"""
        # Headers que Railway puede enviar
        forwarded_proto = request.headers.get("x-forwarded-proto")
        forwarded_scheme = request.headers.get("x-forwarded-scheme") 
        
        # Si la request viene por HTTP, redirigir a HTTPS
        if forwarded_proto == "http" or (not forwarded_proto and request.url.scheme == "http"):
            # Construir URL HTTPS
            https_url = request.url.replace(scheme="https")
            print(f"🔄 HTTP → HTTPS redirect: {request.url} → {https_url}")
            return RedirectResponse(url=str(https_url), status_code=301)
        
        response = await call_next(request)
        
        # Añadir headers de seguridad HTTPS
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response
else:
    print("ℹ️  HTTPS redirect deshabilitado (desarrollo o no-Railway)")

# 3) CORS - CONFIGURACIÓN SIMPLIFICADA
def _as_list(value) -> list[str]:
    """Acepta list directa o string 'a,b,c' proveniente de env."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value).split(",") if v.strip()]

# ✅ DOMINIOS HTTPS ÚNICAMENTE EN PRODUCCIÓN
if is_production:
    allowed_origins = [
        "https://software-loyal-light-jtxufeu11-loyal-lights-projects.vercel.app",
        "https://software-loyal-light.vercel.app",
        "https://softwareloyallight-production.up.railway.app",
    ]
else:
    # En desarrollo, permitir ambos HTTP y HTTPS
    allowed_origins = [
        "https://software-loyal-light-jtxufeu11-loyal-lights-projects.vercel.app",
        "https://software-loyal-light.vercel.app",
        "https://softwareloyallight-production.up.railway.app",
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
    ]

# En debug, permitir todo (para testing)
if settings.DEBUG:
    allowed_origins.append("*")

print(f"[CORS] Configurando CORS con {len(allowed_origins)} orígenes permitidos:")
for origin in allowed_origins:
    print(f"  ✅ {origin}")

# Agregar middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app" if is_production else None,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 🆕 Middleware de debugging mejorado
@app.middleware("http")
async def debug_middleware(request, call_next):
    """Debug middleware para troubleshooting HTTPS + CORS"""
    origin = request.headers.get("origin")
    method = request.method
    path = str(request.url.path)
    scheme = request.url.scheme
    forwarded_proto = request.headers.get("x-forwarded-proto")
    host = request.headers.get("host")
    
    # Log requests importantes
    if method == "OPTIONS" or path in ["/", "/health", "/health/"] or any(x in path for x in ["/auth/", "/analytics/"]):
        print(f"🌐 {method} {scheme}://{host}{path}")
        print(f"   Origin: {origin or 'None'}")
        print(f"   X-Forwarded-Proto: {forwarded_proto or 'None'}")
        print(f"   User-Agent: {request.headers.get('user-agent', 'None')[:50]}...")
    
    response = await call_next(request)
    
    # Log respuesta para rutas importantes
    if path in ["/", "/health", "/health/"]:
        print(f"📤 Response {response.status_code} for {path}")
        security_headers = [k for k in response.headers.keys() if 'security' in k.lower() or k.lower().startswith('strict-transport')]
        if security_headers:
            print(f"   Security headers: {security_headers}")
    
    return response

# 4) Errores globales
register_exception_handlers(app)

# 5) Routers
app.include_router(auth_router,      prefix="/auth",      tags=["auth"])
app.include_router(clients_router,   prefix="/clients",   tags=["clients"])
app.include_router(items_router,     prefix="/items",     tags=["items"])
app.include_router(purchases_router, prefix="/purchases", tags=["purchases"])
app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
app.include_router(ai_router,        prefix="/ai",        tags=["ai"])
app.include_router(admin_router,     prefix="/admin",     tags=["admin"])

# 6) Health endpoints
def _health_response():
    return JSONResponse({
        "status": "ok", 
        "version": settings.VERSION,
        "https_enabled": is_production and is_railway,
        "cors_enabled": True,
        "allowed_origins": len(allowed_origins),
        "environment": os.getenv("RAILWAY_ENVIRONMENT_NAME", "development"),
        "railway_project": bool(os.getenv("RAILWAY_PROJECT_ID")),
        "server": "Railway",
        "message": f"🚂 Backend funcionando ({'HTTPS forced' if is_production and is_railway else 'HTTP allowed'})"
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

# Debug endpoints
@app.get("/test-https", tags=["debug"])
def test_https(request: Request):
    return {
        "message": "HTTPS test endpoint",
        "request_scheme": request.url.scheme,
        "forwarded_proto": request.headers.get("x-forwarded-proto"),
        "host": request.headers.get("host"),
        "url": str(request.url),
        "is_production": is_production,
        "is_railway": is_railway,
        "https_redirect_enabled": is_production and is_railway,
    }

@app.get("/test-cors", tags=["debug"])
def test_cors(request: Request):
    return {
        "message": "CORS test successful!",
        "origin": request.headers.get("origin"),
        "cors_configured": True,
        "https_only": is_production,
        "allowed_origins_count": len(allowed_origins),
    }

# 7) Run
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    
    print("🚂 ===== RAILWAY DEPLOYMENT FIXED =====")
    print(f"🚀 Puerto: {port}")
    print(f"🔧 Debug: {settings.DEBUG}")
    print(f"🔒 HTTPS redirect: {'✅' if is_production and is_railway else '❌'}")
    print(f"🌐 CORS origins: {len(allowed_origins)}")
    print(f"🛡️  TrustedHost: {'✅ Restrictivo' if is_production else '✅ Permisivo'}")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # No reload en producción
        access_log=True,
        log_level="info"
    )
