<<<<<<< Updated upstream
# backend/app/main.py
=======
﻿# backend/app/main.py
>>>>>>> Stashed changes
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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
<<<<<<< Updated upstream
from app.api.admin import router as admin_router  # <- NUEVO: seeding temporal
=======
from app.api.admin import router as admin_router  # seeding temporal
>>>>>>> Stashed changes

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

# 3) CORS
def _as_list(value) -> list[str]:
    """
    Admite list directa o string con comas/espacios desde env.
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    # string
    return [v.strip() for v in str(value).split(",") if v.strip()]

allowed_origins = _as_list(getattr(settings, "ALLOWED_HOSTS", None)) or [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4) Global errors
register_exception_handlers(app)

# 5) Routers
app.include_router(auth_router,      prefix="/auth",      tags=["auth"])
app.include_router(clients_router,   prefix="/clients",   tags=["clients"])
app.include_router(items_router,     prefix="/items",     tags=["items"])
app.include_router(purchases_router, prefix="/purchases", tags=["purchases"])
app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
app.include_router(ai_router,        prefix="/ai",        tags=["ai"])
<<<<<<< Updated upstream
app.include_router(admin_router,     prefix="/admin",     tags=["admin"])  # <- seeding
=======
app.include_router(admin_router,     prefix="/admin",     tags=["admin"])  # seeding
>>>>>>> Stashed changes

# 6) Health (→ barra final)
@app.get("/health/")
def health_check() -> dict:
    return {"status": "ok", "version": settings.VERSION}

# 7) Run local
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
    )
