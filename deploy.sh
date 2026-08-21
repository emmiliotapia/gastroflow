#!/usr/bin/env bash
# ==============================================================================
# Script de Despliegue Automatizado - Casino Intelligent Hub
# Ruta VPS: /opt/smartops/casino-erp
# ==============================================================================

set -e

echo "[INFO] Iniciando despliegue de Casino Intelligent Hub..."

# Ir al directorio del proyecto en el VPS (o directorio actual)
PROJECT_DIR="${1:-/opt/smartops/casino-erp}"

if [ -d "$PROJECT_DIR" ]; then
    echo "[INFO] Cambiando al directorio del proyecto: $PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

# 1. Obtener última versión desde Git
echo "[INFO] Actualizando código desde repositorio remoto..."
git pull origin main || git pull origin master

# 2. Verificar o crear archivo .env si no existe
if [ ! -f .env ]; then
    echo "[WARN] Archivo .env no encontrado. Copiando desde .env.example..."
    cp .env.example .env
fi

# 3. Construir imágenes e iniciar contenedores
echo "[INFO] Reconstruyendo contenedores Docker sin caché..."
docker compose build --no-cache

echo "[INFO] Levantando servicios en segundo plano..."
docker compose up -d

# 4. Esperar a que la base de datos PostgreSQL esté lista
echo "[INFO] Esperando inicialización de base de datos..."
sleep 5

# 5. Ejecutar seeder automático con las fichas técnicas reales
echo "[INFO] Poblando catálogo de insumos, roles y recetas de AyB reales..."
docker compose exec -T backend python -m backend.db.seed_recipes || echo "[WARN] Seeder ejecutado previamente o pendiente."

# 6. Estado final de los contenedores
echo "[SUCCESS] Despliegue completado exitosamente. Estado de los contenedores:"
docker compose ps
