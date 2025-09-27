# backend/app/main.py - VERSIÓN CON ROUTERS ACTIVOS (Railway)
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.core.settings import settings
from app.utils.logging import setup_logging
from app.utils.errors import register_exception_handlers

# ✅ ROUTERS ACTIVOS
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

# 3) CORS - CONFIGURACIÓN
def _as_list(value) -> list[str]:
    """Acepta list directa o string 'a,b,c' proveniente de env."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value).split(",") if v.strip()]

# ✅ DOMINIOS PERMITIDOS
allowed_origins = _as_list(getattr(settings, "ALLOWED_HOSTS", None)) or [
    # Vercel
    "https://software-loyal-light-jtxufeu11-loyal-lights-projects.vercel.app",
    "https://software-loyal-light.vercel.app",

    # Desarrollo local
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",

    # Railway (si sirves frontend desde ahí)
    "https://softwareloyallight-production.up.railway.app",

    # ⚠️ TEMPORAL PARA DEBUG (quita en prod)
    "*",
]

print(f"[CORS] Configurando CORS con {len(allowed_origins)} orígenes permitidos:")
for origin in allowed_origins:
    print(f"  ✅ {origin}")

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

# 🆕 Middleware de debugging CORS
@app.middleware("http")
async def cors_debug_middleware(request, call_next):
    origin = request.headers.get("origin")
    method = request.method
    path = str(request.url.path)

    if method == "OPTIONS" or "/auth/" in path or "/analytics/" in path:
        print(f"🌐 CORS Request: {method} {path}")
        print(f"   Origin: {origin}")
        print(f"   Headers: {dict(request.headers)}")

    response = await call_next(request)

    if method == "OPTIONS" or origin:
        cors_headers = {
            k: v for k, v in response.headers.items()
            if k.lower().startswith('access-control')
        }
        if cors_headers:
            print(f"✅ CORS Headers en respuesta: {cors_headers}")
        else:
            print("❌ Sin headers CORS en respuesta")

    return response

# 4) Errores globales
register_exception_handlers(app)

# 5) ROUTERS
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
        "cors_enabled": True,
        "allowed_origins": allowed_origins[:3],  # muestra algunos por seguridad
        "environment": os.getenv("ENVIRONMENT", "development"),
        "server": "Railway",
        "message": "🚂 Backend funcionando en Railway!"
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

# 🆕 Endpoint específico para test CORS
@app.get("/test-cors", tags=["debug"])
def test_cors():
    return {
        "message": "CORS is working!",
        "server": "Railway",
        "cors_configured": True,
        "frontend_urls": [
            "https://software-loyal-light.vercel.app",
            "https://software-loyal-light-jtxufeu11-loyal-lights-projects.vercel.app"
        ]
    }

# 🧪 Endpoint para verificar configuración
@app.get("/config-check", tags=["debug"])
def config_check():
    return {
        "supabase_configured": bool(os.getenv("SUPABASE_URL")),
        "jwt_configured": bool(os.getenv("JWT_SECRET")),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug_mode": settings.DEBUG,
        "cors_origins": len(allowed_origins),
        "railway_deployment": True
    }

# 7) Run local o en contenedor
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))

    print("🚂 ===== RAILWAY DEPLOYMENT =====")
    print(f"🚀 Iniciando servidor en puerto {port}")
    print(f"🔧 Debug mode: {settings.DEBUG}")
    print(f"🌐 CORS configurado para {len(allowed_origins)} orígenes")
    print("✅ Routers habilitados: auth, clients, items, purchases, analytics, ai, admin")
    print("🎯 Endpoints disponibles: /, /health, /test-cors, /config-check")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
        access_log=True,
        log_level="info" if settings.DEBUG else "warning"
    )
