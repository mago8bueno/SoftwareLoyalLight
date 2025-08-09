# supabase.py - Inicialización del cliente Supabase con validación de tipos
# Se asegura que las variables de entorno de URL y KEY sean cadenas simples

from supabase import create_client, Client
from app.core.settings import settings

# Asegurarse de convertir AnyHttpUrl a str para compatibilidad con la librería supabase-py
SUPABASE_URL: str = str(settings.SUPABASE_URL)
SUPABASE_KEY: str = settings.SUPABASE_KEY

# Crear instancia global de Supabase Client
# - Reutilizable en toda la aplicación
# - Evita pasar accidentalmente tipos incorrectos
supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)