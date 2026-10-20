#!/usr/bin/env bash
# ==============================================================================
# Script de Despliegue Automatizado - GastroFlow
# Ruta VPS: /opt/smartops/gastroflow
# Uso: ./deploy.sh [directorio_proyecto] [--seed]
# ==============================================================================

set -euo pipefail

PROJECT_DIR="${1:-/opt/smartops/gastroflow}"
COMPOSE="docker compose -f docker-compose.gastroflow.yml"

echo "[INFO] Iniciando despliegue de GastroFlow en $PROJECT_DIR..."
cd "$PROJECT_DIR"

# 1. Obtener última versión desde Git
echo "[INFO] Actualizando código desde repositorio remoto..."
git pull origin main || git pull origin master

# 2. El .env es obligatorio (contiene credenciales; nunca se genera con valores por defecto)
if [ ! -f .env ]; then
    echo "[ERROR] Falta .env. Copia .env.gastroflow.example a .env y define credenciales seguras."
    exit 1
fi

# 3. Reconstruir imagen y levantar servicios
echo "[INFO] Reconstruyendo y levantando contenedores..."
$COMPOSE up -d --build

# 4. Esperar a que el backend responda
echo "[INFO] Esperando health check del backend..."
PORT="$(grep -E '^BACKEND_PORT_HOST=' .env | cut -d= -f2 || true)"
PORT="${PORT:-8002}"
for i in $(seq 1 30); do
    if curl -fs "http://localhost:${PORT}/health" > /dev/null; then
        echo "[INFO] Backend saludable."
        break
    fi
    sleep 2
done

# 5. Seeder opcional
if [[ " $* " == *" --seed "* ]]; then
    echo "[INFO] Ejecutando seeder de recetas..."
    $COMPOSE exec -T backend python -m backend.db.seed_recipes || echo "[WARN] Seeder ya ejecutado o con errores."
fi

echo "[SUCCESS] Despliegue completado:"
$COMPOSE ps
