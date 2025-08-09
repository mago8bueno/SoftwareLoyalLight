# backend/app/core/settings.py

from typing import List

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: AnyHttpUrl
    SUPABASE_KEY: str
    SUPABASE_PROJECT_REF: str

    # JWT
    JWT_SECRET: str

    # Frontend público
    NEXT_PUBLIC_SUPABASE_URL: AnyHttpUrl
    NEXT_PUBLIC_SUPABASE_KEY: str
    NEXT_PUBLIC_OPENAI_KEY: str

    # Vercel
    VERCEL_TOKEN: str

    # App metadata
    PROJECT_NAME: str = "LoyaltyApp"
    VERSION: str = "1.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    ALLOWED_HOSTS: List[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Instancia única de configuración para inyección en toda la app
settings = Settings()

# Debug: verificar que Pydantic está cargando las variables de entorno
print("DEBUG: SUPABASE_URL =", settings.SUPABASE_URL)
