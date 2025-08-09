# backend/app/core/settings.py
from typing import List, Optional
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase (obligatorias para el backend)
    SUPABASE_URL: AnyHttpUrl
    SUPABASE_KEY: str
    SUPABASE_PROJECT_REF: str

    # JWT (obligatoria)
    JWT_SECRET: str

    # Frontend público (opcionales para que el backend no crashee si faltan)
    NEXT_PUBLIC_SUPABASE_URL: Optional[AnyHttpUrl] = None
    NEXT_PUBLIC_SUPABASE_KEY: Optional[str] = None
    NEXT_PUBLIC_OPENAI_KEY: Optional[str] = None

    # Vercel (opcional)
    VERCEL_TOKEN: Optional[str] = None

    # Semilla opcional
    SEED_TOKEN: Optional[str] = None

    # App metadata
    PROJECT_NAME: str = "LoyaltyApp"
    VERSION: str = "1.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    ALLOWED_HOSTS: List[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Log mínimo de diagnóstico (sin secretos)
print("DEBUG: SUPABASE_URL =", settings.SUPABASE_URL)
