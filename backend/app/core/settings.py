# backend/app/core/settings.py — VERSIÓN MEJORADA CORS + VERCEL

from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    # =========================
    # Infra obligatoria
    # =========================
    SUPABASE_URL: AnyHttpUrl
    SUPABASE_KEY: str
    SUPABASE_PROJECT_REF: str
    JWT_SECRET: str

    # =========================
    # Frontend (opcionales)
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
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # =========================
    # CORS - CONFIGURACIÓN MEJORADA
    # =========================
    
    # Acepta tanto lista como string separado por comas
    ALLOWED_ORIGINS: Union[List[str], str] = [
        # Producción Vercel - TODOS los dominios posibles
        "https://software-loyal-light.vercel.app",
        "https://software-loyal-light-git-main-loyal-lights-projects.vercel.app", 
        "https://software-loyal-light-jtxufeu11-loyal-lights-projects.vercel.app",
        
        # Desarrollo local
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000", 
        "http://127.0.0.1:5173",
    ]
    
    @field_validator('ALLOWED_ORIGINS')
    @classmethod
    def parse_origins(cls, v):
        """Convierte string separado por comas en lista."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v or []

    # Otros settings
    VERCEL_TOKEN: Optional[str] = None
    SEED_TOKEN: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        
        # Permite variables de entorno que no están definidas
        extra = "ignore"


# ===== INSTANCIA GLOBAL =====
settings = Settings()

# ===== LOGGING DE CONFIGURACIÓN =====
def log_settings():
    """Log seguro de configuración sin exponer secretos."""
    env = settings.ENVIRONMENT
    debug = settings.DEBUG
    
    print(f"[CONFIG] ===== CONFIGURACIÓN {settings.PROJECT_NAME} v{settings.VERSION} =====")
    print(f"[CONFIG] Entorno: {env}")
    print(f"[CONFIG] Debug: {debug}")
    
    # CORS origins
    origins = settings.ALLOWED_ORIGINS
    if isinstance(origins, list):
        print(f"[CONFIG] CORS Orígenes ({len(origins)}):")
        for i, origin in enumerate(origins, 1):
            print(f"[CONFIG]   {i}. {origin}")
    else:
        print(f"[CONFIG] CORS Orígenes: {origins}")
    
    # URLs (sin mostrar keys)
    print(f"[CONFIG] Supabase URL: {str(settings.SUPABASE_URL)}")
    print(f"[CONFIG] Supabase Key: {'*' * len(str(settings.SUPABASE_KEY)[:8]) + '...'}")
    print(f"[CONFIG] JWT Secret: {'Configurado' if settings.JWT_SECRET else 'No configurado'}")
    
    # Vercel
    vercel_token = "Configurado" if settings.VERCEL_TOKEN else "No configurado"
    print(f"[CONFIG] Vercel Token: {vercel_token}")
    
    print(f"[CONFIG] ===== FIN CONFIGURACIÓN =====")

# Log solo si es desarrollo o debug está activado
if settings.DEBUG or os.getenv("LOG_CONFIG") == "1":
    log_settings()
