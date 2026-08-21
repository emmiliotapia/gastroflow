# Topología del VPS y Puertos (`map.md`)

## Entorno de Producción VPS (`smartops`)
- **Directorio Raíz en VPS:** `/opt/smartops/casino-erp`
- **Red Aislada Docker:** `casino_net` (Bridge independiente)

## Mapeo de Puertos y Servicios (Anti-Colisión)
- **FastAPI Core Backend:**
  - Puerto Host VPS: `http://localhost:8001`
  - Puerto Contenedor: `8000`
  - Documentación OpenAPI: `http://localhost:8001/docs`
  - Healthcheck: `http://localhost:8001/health`
- **PostgreSQL + pgvector Database:**
  - Puerto Host VPS: `5433` (Aislado de n8n y de otras BDs en `5432`)
  - Puerto Contenedor: `5432`
  - Usuario: `${POSTGRES_USER}` (`casino_admin`)
  - Base de Datos: `casino_erp_db`
  - Volumen Persistente: `pgdata_casino`
- **n8n Webhooks (Integración Externa):** `http://localhost:5678`
- **PWA Frontend:** `http://localhost:3000` (Servido estáticamente o por Nginx)

## Repositorio Git Oficial
- **Remote:** `git@github.com:emmiliotapia/PRESTIGE.git`
- **Script de Despliegue en VPS:** `./deploy.sh`
