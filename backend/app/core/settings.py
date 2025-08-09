# backend/app/core/settings.py
from typing import List, Optional
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ===== Supabase =====
    SUPABASE_URL: AnyHttpUrl
    SUPABASE_KEY: str
    SUPABASE_PROJECT_REF: str

    # ===== JWT =====
    JWT_SECRET: str

    # ===== Frontend público (las usa el backend en respuestas/diagnóstico si quieres) =====
    NEXT_PUBLIC_SUPABASE_URL: AnyHttpUrl
    NEXT_PUBLIC_SUPABASE_KEY: str
    NEXT_PUBLIC_OPENAI_KEY: str

    # ===== Vercel (opcional para scripts) =====
    VERCEL_TOKEN: Optional[str] = None

    # ===== Admin / utilidades =====
    SEED_TOKEN: Optional[str] = None  # <- token para endpoint de seed. Déjalo vacío tras usarlo.

    # ===== App metadata =====
    PROJECT_NAME: str = "LoyaltyApp"
    VERSION: str = "1.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    ALLOWED_HOSTS: List[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Instancia única de configuración
settings = Settings()

# (Opcional) Log básico controlado por DEBUG
if settings.DEBUG:
    print("DEBUG: SUPABASE_URL =", settings.SUPABASE_URL)
