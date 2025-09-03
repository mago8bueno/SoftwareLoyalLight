# backend/app/main.py — VERSIÓN CORREGIDA (CORS OK + health + debug opcional)

import os
import uvicorn
from typing import Iterable, List

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

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
from app.api.admin import router as admin_router  # seeding temporal


# =========================================================
# Utilidades
# =========================================================

def _as_list(value) -> List[str]:
    """Acepta list/tuple o string 'a,b,c' (env). Normaliza y filtra vacíos."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value).split(",") if v.strip()]


def _allowed_origins() -> List[str]:
    """
    Prioridad:
      1) settings.ALLOWED_ORIGINS (pydantic)
      2) env ALLOWED_ORIGINS (comma-separated)
      3) fallback por defecto (producción + local)
    """
    # Nombre canónico en settings: ALLOWED_ORIGINS
    s = getattr(settings, "ALLOWED_ORIGINS", None)
    env = os.getenv("ALLOWED_ORIGINS", None)

    origins = _as_list(s) or _as_list(env) or [
        # Producción (dominios exactos de Vercel que usas)
        "https://software-loyal-light-jtxufeu11-loyal-lights-projects.vercel.app",
        "https://software-loyal-light.vercel.app",

        # Desarrollo local (Vite / Next)
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Nunca uses "*" con allow_credentials=True
    # No es necesario incluir el propio dominio del backend.
    return origins


# =========================================================
# App base
# =========================================================

# 1) Logging temprano
setup_logging()

# 2) FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# 3) CORS (debe ir ANTES de incluir routers y suficiente para OPTIONS)
allowed_origins = _allowed_origins()

print(f"[CORS] Orígenes permitidos ({len(allowed_origins)}):")
for o in allowed_origins:
    print(f"  • {o}")

# Nota: permitimos regex para previews/branches de Vercel del mismo proyecto
VERCEL_REGEX = r"https://software-loyal-light.*\.vercel\.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,                     # lista exacta
    allow_origin_regex=VERCEL_REGEX,                   # previews de Vercel
    allow_credentials=True,                            # si usas cookies ahora o futuro
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "Cache-Control",
    ],
    expose_headers=[
        # expón lo que verdaderamente necesites leer desde el frontend
        "Content-Length",
        "Content-Type",
        "Date",
        "Server",
    ],
    max_age=86400,  # cache del preflight en el navegador (24h)
)

# 3.1) Debug CORS opcional (activar con env DEBUG_CORS=1)
DEBUG_CORS = os.getenv("DEBUG_CORS", "0") == "1"

if DEBUG_CORS:
    @app.middleware("http")
    async def cors_debug_middleware(request: Request, call_next):
        origin = request.headers.get("origin")
        method = request.method
        path = str(request.url.path)
        if method == "OPTIONS" or "/auth/" in path or "/analytics/" in path:
            print(f"🌐 CORS Request: {method} {path}")
            print(f"   Origin: {origin}")
            # Cuidado: no loguees Authorization en producción
            safe_headers = {k: v for k, v in request.headers.items() if k.lower() != "authorization"}
            print(f"   Headers: {safe_headers}")

        response = await call_next(request)

        if method == "OPTIONS" or origin:
            cors_headers = {k: v for k, v in response.headers.items() if k.lower().startswith("access-control")}
            if cors_headers:
                print(f"✅ CORS en respuesta: {cors_headers}")
            else:
                print("❌ Respuesta sin headers CORS")

        return response

# 4) Static /media (opcional)
MEDIA_DIR = os.path.join(os.getcwd(), "media")
os.makedirs(MEDIA_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

# 5) Errores globales
register_exception_handlers(app)

# 6) Routers (después de CORS)
app.include_router(auth_router,      prefix="/auth",      tags=["auth"])
app.include_router(clients_router,   prefix="/clients",   tags=["clients"])
app.include_router(items_router,     prefix="/items",     tags=["items"])
app.include_router(purchases_router, prefix="/purchases", tags=["purchases"])
app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
app.include_router(ai_router,        prefix="/ai",        tags=["ai"])
app.include_router(admin_router,     prefix="/admin",     tags=["admin"])

# 7) Health + Root
def _health_response() -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "version": settings.VERSION,
        "cors_enabled": True,
        "allowed_origins_count": len(allowed_origins),
        "environment": os.getenv("ENVIRONMENT", "development"),
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

@app.get("/test-cors", tags=["debug"])
def test_cors():
    return {
        "message": "CORS OK",
        "regex": VERCEL_REGEX,
        "debug_cors": DEBUG_CORS,
    }

# 8) Run local
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Iniciando servidor en 0.0.0.0:{port}")
    print(f"🔧 DEBUG={settings.DEBUG} | DEBUG_CORS={DEBUG_CORS}")
    print(f"🌐 Previews Vercel permitidos por regex: {VERCEL_REGEX}")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
        access_log=True,
        log_level="debug" if settings.DEBUG else "info",
    )
