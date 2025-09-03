# backend/app/main.py — VERSIÓN CORREGIDA CORS + PREFLIGHT + JWT

import os
import uvicorn
from typing import Iterable, List

from fastapi import FastAPI, Request, HTTPException
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
from app.api.admin import router as admin_router


# =========================================================
# CORS CORREGIDO - Manejo completo de preflight + JWT
# =========================================================

def _get_cors_origins() -> List[str]:
    """
    Obtiene lista de orígenes permitidos con fallbacks robustos.
    """
    # Intenta desde settings primero
    if hasattr(settings, 'ALLOWED_ORIGINS') and settings.ALLOWED_ORIGINS:
        origins = [str(origin) for origin in settings.ALLOWED_ORIGINS]
        print(f"[CORS] Usando orígenes desde settings: {len(origins)} configurados")
        return origins
    
    # Fallback desde env
    env_origins = os.getenv("ALLOWED_ORIGINS", "")
    if env_origins:
        origins = [o.strip() for o in env_origins.split(",") if o.strip()]
        print(f"[CORS] Usando orígenes desde ENV: {len(origins)} configurados")
        return origins
    
    # Fallback hardcoded para desarrollo
    default_origins = [
        # Producción - dominios exactos de Vercel
        "https://software-loyal-light.vercel.app",
        "https://software-loyal-light-jtxufeu11-loyal-lights-projects.vercel.app",
        
        # Desarrollo local - puertos comunes
        "http://localhost:3000",
        "http://localhost:5173", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
    print(f"[CORS] Usando orígenes por defecto: {len(default_origins)} configurados")
    return default_origins


# =========================================================
# Aplicación principal
# =========================================================

# 1) Setup inicial
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# 2) CORS - CONFIGURACIÓN CRÍTICA CORREGIDA
cors_origins = _get_cors_origins()

print(f"[CORS] ===== CONFIGURACIÓN CORS =====")
print(f"[CORS] Orígenes permitidos:")
for i, origin in enumerate(cors_origins, 1):
    print(f"[CORS]   {i}. {origin}")

# Regex más amplia para previews de Vercel
VERCEL_PREVIEW_REGEX = r"https://software-loyal-light-.*\.vercel\.app"

app.add_middleware(
    CORSMiddleware,
    # Orígenes exactos
    allow_origins=cors_origins,
    
    # Regex para previews/branches de Vercel  
    allow_origin_regex=VERCEL_PREVIEW_REGEX,
    
    # CRÍTICO: debe ser True para requests con Authorization
    allow_credentials=True,
    
    # MÉTODOS COMPLETOS incluyendo OPTIONS
    allow_methods=[
        "GET", 
        "POST", 
        "PUT", 
        "PATCH", 
        "DELETE", 
        "OPTIONS",  # CRÍTICO para preflight
        "HEAD"
    ],
    
    # HEADERS CRÍTICOS para JWT + requests normales
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Authorization",      # CRÍTICO para JWT
        "Content-Type",
        "Content-Language",
        "Origin",
        "X-Requested-With",
        "X-CSRF-Token",
        "X-User-ID",         # Si lo usas en el frontend
        "Cache-Control",
        "Pragma",
    ],
    
    # Headers expuestos al frontend
    expose_headers=[
        "Content-Length",
        "Content-Type", 
        "Date",
        "Server",
        "X-Request-ID",
    ],
    
    # Cache de preflight más largo
    max_age=3600,  # 1 hora
)

print(f"[CORS] Regex Vercel: {VERCEL_PREVIEW_REGEX}")
print(f"[CORS] Credentials: True")
print(f"[CORS] Max age: 3600s")
print(f"[CORS] ===== FIN CONFIGURACIÓN =====")

# 3) Middleware adicional para debug CORS (opcional)
if settings.DEBUG or os.getenv("DEBUG_CORS") == "1":
    @app.middleware("http")
    async def debug_cors_middleware(request: Request, call_next):
        method = request.method
        path = str(request.url.path)
        origin = request.headers.get("origin")
        
        # Log solo requests importantes
        if method == "OPTIONS" or "analytics" in path or "auth" in path:
            print(f"🌐 [{method}] {path}")
            print(f"   Origin: {origin}")
            print(f"   User-Agent: {request.headers.get('user-agent', 'N/A')[:50]}...")
            
            # Headers de authorization (sin mostrar el token completo)
            auth_header = request.headers.get("authorization", "")
            if auth_header:
                print(f"   Auth: {auth_header[:20]}...")
            
        response = await call_next(request)
        
        # Log respuesta de preflight
        if method == "OPTIONS":
            cors_headers = {
                k: v for k, v in response.headers.items() 
                if k.lower().startswith("access-control")
            }
            print(f"   ✅ CORS Response Headers: {list(cors_headers.keys())}")
            print(f"   Status: {response.status_code}")
        
        return response

# 4) Manejo explícito de OPTIONS para todas las rutas
@app.options("/{full_path:path}")
async def preflight_handler(request: Request, full_path: str):
    """
    Manejo explícito de preflight OPTIONS para todas las rutas.
    Esto asegura que siempre devolvamos 200 OK para preflight.
    """
    origin = request.headers.get("origin")
    
    # Verificar que el origen está permitido
    if origin and (origin in cors_origins or any(origin.endswith(suffix) for suffix in [".vercel.app"])):
        return JSONResponse(
            status_code=200,
            content={"status": "preflight ok"},
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD",
                "Access-Control-Allow-Headers": "Accept, Authorization, Content-Type, Origin, X-Requested-With, X-User-ID",
                "Access-Control-Max-Age": "3600",
            }
        )
    
    # Origen no permitido
    return JSONResponse(
        status_code=204,  # No content pero sin headers CORS
        content=None
    )

# 5) Static files
MEDIA_DIR = os.path.join(os.getcwd(), "media") 
os.makedirs(MEDIA_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

# 6) Manejadores de errores
register_exception_handlers(app)

# 7) Routers - ORDEN IMPORTANTE
app.include_router(auth_router,      prefix="/auth",      tags=["auth"])
app.include_router(clients_router,   prefix="/clients",   tags=["clients"])  
app.include_router(items_router,     prefix="/items",     tags=["items"])
app.include_router(purchases_router, prefix="/purchases", tags=["purchases"])
app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
app.include_router(ai_router,        prefix="/ai",        tags=["ai"])
app.include_router(admin_router,     prefix="/admin",     tags=["admin"])

# 8) Endpoints de salud y debug
@app.get("/")
@app.head("/") 
@app.options("/")  # Agregar OPTIONS también aquí
def root():
    return JSONResponse({
        "status": "healthy",
        "service": "loyalty-backend",
        "version": settings.VERSION,
        "cors_origins": len(cors_origins),
        "environment": os.getenv("ENVIRONMENT", "development"),
    })

@app.api_route("/health", methods=["GET", "HEAD", "OPTIONS"])
@app.api_route("/health/", methods=["GET", "HEAD", "OPTIONS"])  
def health_check():
    return JSONResponse({
        "status": "ok",
        "timestamp": "2025-01-21T12:00:00Z",
        "version": settings.VERSION,
        "cors_enabled": True,
        "allowed_origins_count": len(cors_origins),
    })

@app.get("/cors-test", tags=["debug"])
def cors_test():
    """Endpoint para probar CORS desde el frontend."""
    return {
        "message": "CORS está funcionando correctamente",
        "origins_configured": len(cors_origins),
        "regex_pattern": VERCEL_PREVIEW_REGEX,
        "credentials_allowed": True,
        "server_time": "2025-01-21T12:00:00Z",
    }

# 9) Arranque local
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    
    print(f"🚀 ===== INICIANDO SERVIDOR =====")
    print(f"🚀 Host: 0.0.0.0")
    print(f"🚀 Puerto: {port}")
    print(f"🚀 Debug: {settings.DEBUG}")
    print(f"🚀 Entorno: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"🚀 CORS Orígenes: {len(cors_origins)}")
    print(f"🚀 ===== SERVIDOR LISTO =====")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
        access_log=True,
        log_level="debug" if settings.DEBUG else "info",
    )
