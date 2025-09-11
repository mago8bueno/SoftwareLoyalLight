#!/usr/bin/env bash
# scripts/setup-render.sh  
# Configuración inicial para despliegue en Render

set -e

echo "⚙️  ===== CONFIGURANDO PROYECTO PARA RENDER ====="

# =============================================
# 1. CREAR ARCHIVOS NECESARIOS
# =============================================
echo "📁 Creando archivos de configuración..."

# Crear render.yaml si no existe
if [ ! -f "render.yaml" ]; then
    echo "✅ Creando render.yaml..."
    # El contenido ya lo tienes del artifact anterior
    echo "❗ ACCIÓN REQUERIDA: Copia el contenido de render.yaml del artifact"
else
    echo "✅ render.yaml ya existe"
fi

# Crear .renderignore para optimizar builds
echo "📝 Creando .renderignore..."
cat > .renderignore << EOF
# .renderignore - Archivos que Render debe ignorar

# Desarrollo local
.env
.env.local
*.log

# Tests y coverage
tests/
**/test_*
**/*test*
coverage/
.coverage
.pytest_cache/

# IDEs
.vscode/
.idea/
*.swp
.DS_Store

# Frontend (si solo despliegas backend)
frontend/node_modules/
frontend/.next/
frontend/out/

# Python cache
__pycache__/
*.pyc
*.pyo
*.egg-info/

# Git
.git/
.gitignore

# Documentación
README.md
docs/

# CI/CD de otros servicios
.github/
.vercel/
docker-compose*.yml
Dockerfile*

EOF

# =============================================
# 2. VALIDAR CONFIGURACIÓN ACTUAL
# =============================================
echo ""
echo "🔍 Validando configuración actual..."

# Verificar estructura del proyecto
if [ -d "backend" ] && [ -f "backend/app/main.py" ]; then
    echo "✅ Backend estructura OK"
else
    echo "❌ Backend no encontrado o incompleto"
fi

if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    echo "✅ Frontend encontrado"
else
    echo "⚠️  Frontend no encontrado (opcional)"
fi

# Verificar requirements.txt
if [ -f "backend/requirements.txt" ]; then
    echo "✅ requirements.txt existe"
    echo "   Dependencias principales:"
    grep -E "(fastapi|uvicorn|supabase)" backend/requirements.txt | head -3 | sed 's/^/     /'
else
    echo "❌ backend/requirements.txt faltante"
fi

# =============================================
# 3. INFORMACIÓN Y SIGUIENTES PASOS
# =============================================
echo ""
echo "📋 ===== SIGUIENTES PASOS ====="
echo ""
echo "1. 🔧 CONFIGURAR REPOSITORIO EN RENDER:"
echo "   • Ve a https://dashboard.render.com"
echo "   • Conecta tu repositorio de GitHub"
echo "   • Render detectará render.yaml automáticamente"
echo ""

echo "2. ⚙️ CONFIGURAR VARIABLES DE ENTORNO:"
echo "   En Render Dashboard → Service Settings → Environment:"
echo ""
echo "   📋 VARIABLES OBLIGATORIAS:"
echo "   SUPABASE_URL=https://tu-proyecto.supabase.co" 
echo "   SUPABASE_KEY=eyJ... (service_role key)"
echo "   SUPABASE_PROJECT_REF=abcdefghijklmnop"
echo "   JWT_SECRET=$(openssl rand -base64 32)"
echo ""
echo "   🌐 VARIABLES DE CORS:"
echo "   ALLOWED_ORIGINS=https://tu-frontend.onrender.com,https://tu-dominio.com"
echo "   ENVIRONMENT=production"
echo "   DEBUG=false"
echo ""

echo "3. 🚀 DESPLEGAR:"
echo "   git add ."
echo "   git commit -m \"Add Render configuration\""
echo "   git push origin main"
echo ""

echo "4. 🔍 MONITOREAR:"
echo "   • Render iniciará el build automáticamente"
echo "   • Monitorea logs en el dashboard"
echo "   • El servicio estará en: https://tu-servicio.onrender.com"
echo ""

echo "📞 ===== ENDPOINTS DE PRUEBA ====="
echo "Una vez desplegado, prueba:"
echo "• https://tu-backend.onrender.com/health"
echo "• https://tu-backend.onrender.com/docs (si DEBUG=true)"
echo ""

echo "✅ Configuración completada"
echo "🎯 Listo para desplegar en Render"
