# backend/app/core/settings.py — VERSIÓN CORREGIDA (CORS + tipos + seguridad)
from typing import List, Optional
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # =========================
    # Infra obligatoria
    # =========================
    SUPABASE_URL: AnyHttpUrl
    SUPABASE_KEY: str
    SUPABASE_PROJECT_REF: str

    # JWT
    JWT_SECRET: str

    # =========================
    # Frontend público (opcionales)
    # =========================
    NEXT_PUBLIC_SUPABASE_URL: Optional[AnyHttpUrl] = None
    NEXT_PUBLIC_SUPABASE_KEY: Optional[str] = None
    NEXT_PUBLIC_OPENAI_KEY: Optional[str] = None

    # =========================
    # App metadata
    # =========================
    PROJECT_NAME: str = "LoyaltyApp"
    VERSION: str = "1.0.0"
    PORT: int = 8000

    # Entorno
    DEBUG: bool = False  # Producción por defecto; cambia en .env
    ENVIRONMENT: str = "development"  # development | staging | production

    # =========================
    # CORS — usa SIEMPRE dominios explícitos
    # =========================
    # Puedes sobreescribir por .env con:
    # ALLOWED_ORIGINS='["https://tu-dominio.vercel.app","http://localhost:5173"]'
    ALLOWED_ORIGINS: List[AnyHttpUrl] = [
        # Producción (Vercel)
        "https://software-loyal-light.vercel.app",
        "https://software-loyal-light-jtxufeu11-loyal-lights-projects.vercel.app",
        # Desarrollo local (Vite/Next)
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # (DEPRECADO) Se mantiene para retrocompatibilidad, pero NO se usa en CORS
    ALLOWED_HOSTS: List[str] = []

    # Otros (opcionales)
    VERCEL_TOKEN: Optional[str] = None
    SEED_TOKEN: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# =========================
# Log mínimo de diagnóstico
# =========================
# Evita imprimir secretos y URLs sensibles en producción
if settings.DEBUG or settings.ENVIRONMENT != "production":
    print(f"[SETTINGS] ENVIRONMENT={settings.ENVIRONMENT} | DEBUG={settings.DEBUG}")
    print(f"[SETTINGS] PROJECT_NAME={settings.PROJECT_NAME} v{settings.VERSION}")
    print(f"[SETTINGS] ALLOWED_ORIGINS ({len(settings.ALLOWED_ORIGINS)}):")
    for o in settings.ALLOWED_ORIGINS:
        print(f"  • {o}")
