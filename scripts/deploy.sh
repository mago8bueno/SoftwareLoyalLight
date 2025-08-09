#!/usr/bin/env bash
# scripts/deploy.sh
# Propósito: Construir la imagen Docker, aplicar migraciones en Supabase y desplegar en Vercel.

set -o errexit    # Salir si cualquier comando falla
set -o pipefail   # Capturar errores en pipelines
IFS=$'\n\t'

# Cargar variables de entorno
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
else
  echo "⚠️  .env no encontrado; asegúrate de configurar SUPABASE_URL, SUPABASE_KEY y VERCEL_TOKEN"
  exit 1
fi

# 1. Build de Docker
echo "🔨 Construyendo imagen Docker..."
docker build -t loyaltyapp-backend:latest backend/

# 2. Ejecutar migraciones en Supabase
echo "🗄️  Aplicando migraciones en Supabase..."
# Requiere supabase CLI autenticado: `supabase login`
supabase db push --project-ref "$SUPABASE_PROJECT_REF"

# 3. Despliegue en Vercel
echo "🚀 Desplegando en Vercel..."
# Requiere VERCEL_TOKEN en .env y vercel CLI instalado
vercel --prod --confirm

echo "✅ Despliegue completado con éxito."

# Buenas prácticas:
# - Gestión de secretos en .env, nunca hardcodear claves.
# - Idempotencia: etiquetas de imagen fijas y migraciones push seguras.
# - Manejo de errores: set -e y pipefail abortan en fallo.
# - Documentar pre-requisitos: supabase & vercel CLIs.
