#!/usr/bin/env bash
# ==============================================================================
# Script de Despliegue Automatizado - Casino Intelligent Hub
# Ruta VPS: /opt/smartops/casino-erp
# ==============================================================================

set -e

echo "🚀 Iniciando despliegue de Casino Intelligent Hub..."

# Ir al directorio del proyecto en el VPS (o directorio actual)
PROJECT_DIR="${1:-/opt/smartops/casino-erp}"

if [ -d "$PROJECT_DIR" ]; then
    echo "📁 Cambiando al directorio del proyecto: $PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

# 1. Obtener última versión desde Git
echo "📥 Actualizando código desde repositorio remoto..."
git pull origin main || git pull origin master

# 2. Verificar o crear archivo .env si no existe
if [ ! -f .env ]; then
    echo "⚠️ Archivo .env no encontrado. Copiando desde .env.example..."
    cp .env.example .env
fi

# 3. Construir imágenes e iniciar contenedores
echo "🐳 Reconstruyendo contenedores Docker sin caché..."
docker compose build --no-cache

echo "🔄 Levantando servicios en segundo plano..."
docker compose up -d

# 4. Estado de los contenedores
echo "✅ Despliegue completado exitosamente. Estado de los contenedores:"
docker compose ps
