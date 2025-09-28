# backend/app/main.py - VERSIÓN CON HTTPS FORZADO
import os
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
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

# 🔒 2.2) HTTPS MIDDLEWARE - AÑADIR ANTES DE CORS
# Solo en producción Railway
is_production = os.getenv("ENVIRONMENT") == "production" or os.getenv("RAILWAY_ENVIRONMENT_NAME") == "production"
is_railway = "railway.app" in os.getenv("RAILWAY_STATIC_URL", "") or os.getenv("RAILWAY_PROJECT_ID")

print(f"🔍 Environment check:")
print(f"   ENVIRONMENT: {os.getenv('ENVIRONMENT', 'not set')}")
print(f"   RAILWAY_ENVIRONMENT_NAME: {os.getenv('RAILWAY_ENVIRONMENT_NAME', 'not set')}")
print(f"   Is production: {is_production}")
print(f"   Is Railway: {is_railway}")

if is_production and is_railway:
    print("🔒 HABILITANDO HTTPS REDIRECT EN PRODUCCIÓN RAILWAY")
    
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

    # Trusted hosts middleware  
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=[
            "softwareloyallight-production.up.railway.app",
            "*.up.railway.app",
            "software-loyal-light.vercel.app",
            "software-loyal-light-*.vercel.app",
            "localhost",
            "127.0.0.1"
        ]
    )
else:
    print("ℹ️  HTTPS redirect deshabilitado (desarrollo o no-Railway)")

# 3) CORS - CONFIGURACIÓN CORREGIDA
def _as_list(value) -> list[str]:
    """Acepta list directa o string 'a,b,c' proveniente de env."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value).split(",") if v.strip()]

# ✅ DOMINIOS CORREGIDOS - FORZAR HTTPS EN PRODUCCIÓN
allowed_origins = _as_list(getattr(settings, "ALLOWED_HOSTS", None)) or [
    # 🔧 DOMINIOS DE VERCEL (solo HTTPS)
    "https://software-loyal-light-jtxufeu11-loyal-lights-projects.vercel.app",
    "https://software-loyal-light.vercel.app",
    
    # Railway mismo (solo HTTPS en producción)
    "https://softwareloyallight-production.up.railway.app",
]

# Añadir localhost solo en desarrollo
if not is_production:
    allowed_origins.extend([
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
    ])

# En desarrollo, permitir todo temporalmente
if settings.DEBUG:
    allowed_origins.append("*")

print(f"[CORS] Configurando CORS con {len(allowed_origins)} orígenes permitidos:")
for origin in allowed_origins:
    print(f"  ✅ {origin}")

# Agregar middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://software-loyal-light.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=[
        "*",
        "Authorization",
        "Content-Type", 
        "X-User-Id",
        "Accept",
        "Origin",
        "User-Agent",
        "X-Requested-With",
        "Cache-Control",
    ],
    expose_headers=[
        "Content-Length",
        "Content-Type",
        "Date",
        "Server",
    ],
)

# 🆕 Middleware de debugging CORS mejorado
@app.middleware("http")
async def cors_debug_middleware(request, call_next):
    """Debug middleware para troubleshooting CORS + HTTPS"""
    origin = request.headers.get("origin")
    method = request.method
    path = str(request.url.path)
    scheme = request.url.scheme
    forwarded_proto = request.headers.get("x-forwarded-proto")
    
    # Log requests importantes con info HTTPS
    if method == "OPTIONS" or "/auth/" in path or "/analytics/" in path:
        print(f"🌐 Request: {method} {scheme}://{request.url.netloc}{path}")
        print(f"   Origin: {origin}")
        print(f"   Scheme: {scheme}")
        print(f"   X-Forwarded-Proto: {forwarded_proto}")
    
    response = await call_next(request)
    
    # Verificar headers CORS en respuesta
    if method == "OPTIONS" or origin:
        cors_headers = {
            k: v for k, v in response.headers.items() 
            if k.lower().startswith('access-control')
        }
        security_headers = {
            k: v for k, v in response.headers.items()
            if k.lower() in ['strict-transport-security', 'x-content-type-options']
        }
        if cors_headers:
            print(f"✅ CORS Headers: {cors_headers}")
        if security_headers:
            print(f"🔒 Security Headers: {security_headers}")
    
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

# 6) Health + Root endpoint
def _health_response():
    return JSONResponse({
        "status": "ok", 
        "version": settings.VERSION,
        "https_enabled": is_production and is_railway,
        "cors_enabled": True,
        "allowed_origins": len(allowed_origins),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "railway_env": os.getenv("RAILWAY_ENVIRONMENT_NAME", "not-railway"),
        "server": "Railway",
        "message": f"🚂 Backend funcionando en Railway ({'HTTPS' if is_production else 'HTTP'})!"
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

# 🆕 Endpoint específico para test HTTPS
@app.get("/test-https", tags=["debug"])
def test_https(request: Request):
    return {
        "message": "HTTPS test endpoint",
        "request_scheme": request.url.scheme,
        "forwarded_proto": request.headers.get("x-forwarded-proto"),
        "forwarded_scheme": request.headers.get("x-forwarded-scheme"),
        "host": request.url.netloc,
        "is_production": is_production,
        "is_railway": is_railway,
        "https_redirect_enabled": is_production and is_railway,
        "timestamp": "2025-01-21T12:00:00Z"
    }

@app.get("/test-cors", tags=["debug"])
def test_cors():
    return {
        "message": "CORS is working!",
        "timestamp": "2025-01-21T12:00:00Z",
        "server": "Railway",
        "cors_configured": True,
        "https_only": is_production,
        "frontend_urls": [
            "https://software-loyal-light.vercel.app",
            "https://software-loyal-light-jtxufeu11-loyal-lights-projects.vercel.app"
        ]
    }

@app.get("/config-check", tags=["debug"])
def config_check():
    return {
        "supabase_configured": bool(os.getenv("SUPABASE_URL")),
        "jwt_configured": bool(os.getenv("JWT_SECRET")),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "railway_environment": os.getenv("RAILWAY_ENVIRONMENT_NAME"),
        "debug_mode": settings.DEBUG,
        "cors_origins": len(allowed_origins),
        "https_redirect": is_production and is_railway,
        "railway_deployment": True
    }

# 7) Run
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    
    print("🚂 ===== RAILWAY DEPLOYMENT =====")
    print(f"🚀 Iniciando servidor en puerto {port}")
    print(f"🔧 Debug mode: {settings.DEBUG}")
    print(f"🔒 HTTPS redirect: {'✅ Habilitado' if is_production and is_railway else '❌ Deshabilitado'}")
    print(f"🌐 CORS configurado para {len(allowed_origins)} orígenes")
    print("🎯 Endpoints: /, /health, /test-https, /test-cors, /config-check")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
        access_log=True,
        log_level="info" if settings.DEBUG else "warning"
    )
