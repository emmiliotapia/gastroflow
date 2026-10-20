# 🧭 GastroFlow OS — Documento Guía de Continuidad (`resumen.md`)

> **Propósito:** Esta guía está diseñada para que cualquier agente de IA o desarrollador pueda tomar el proyecto, entenderlo en minutos y continuar su desarrollo o mantenimiento sin fricciones ni riesgos de colisión en producción.

---

## 📌 1. ¿Qué es GastroFlow OS y qué hace el proyecto?
**GastroFlow OS** es un ecosistema operativo y tecnológico modular para el sector gastronómico (restaurantes, bares, cafeterías y dark kitchens).
El sistema resuelve la desconexión operativa entre salón, cocina y administración a través de interfaces web ligeras (PWAs) sincronizadas en tiempo real:

1. **Menú Digital QR y Autopedidos (`frontend/cliente.html`):** Los clientes piden desde la mesa sin instalar aplicaciones, consultan alérgenos y fotos, y pueden solicitar asistencia o cuenta.
2. **Comandero Móvil para Meseros (`frontend/pos.html`):** Permite levantar pedidos a pie de mesa desde cualquier smartphone o tablet y mandarlos al instante a cocina/barra con notas y modificadores.
3. **Monitor KDS de Cocina y Barra (`frontend/kds.html`):** Pantalla en tiempo real conectada por WebSockets que ordena las comandas en cola FIFO con semáforo de tiempos (Verde, Ámbar, Rojo +15m) y alertas acústicas.
4. **Punto de Venta / Terminal de Caja (`frontend/cashier.html`):** Cobro multiformato (efectivo, tarjetas), división de cuentas entre comensales, control de propinas y arqueo ciego protegido por PIN.
5. **Escandallos y Fichas Técnicas (`frontend/catalogo.html`):** Control estricto del costo unitario por receta, margen bruto y deducción automática de insumos con cada venta.
6. **Consola de Alertas Operativas (`frontend/alerts.html`):** Transmisión de eventos de mesa lista o platos demorados hacia el celular del personal vía webhooks y servidor push.
7. **Portal Comercial & Cotizador (`frontend/index.html`):** Catálogo de cara al cliente con explicaciones sencillas (no técnicas) y simulador interactivo para cotizar tanto el software como el equipamiento físico (estaciones KDS, impresoras térmicas, cajones de dinero, etc.).

---

## 🗺️ 2. Mapa de Archivos: ¿Qué hay dentro de cada documento y qué leer?

Para entender el proyecto en orden recomendado, sigue esta secuencia:

### Fase 1: Arquitectura y Especificaciones
* **[`README.md`](README.md):** Visión general comercial, propuesta de valor, hardware compatible y arranque rápido.
* **[`blueprint.md`](blueprint.md):** Especificación técnica profunda de los flujos de datos, modelos relacionales, endpoints de API y diagramas del sistema.
* **[`estructura.md`](estructura.md):** Árbol de directorios y propósito de cada carpeta de backend y frontend.
* **[`map.md`](map.md):** Mapa de red, puertos y enrutamiento en Nginx Proxy Manager (NPM).

### Fase 2: Reglas de Trabajo, Tareas y Errores Conocidos
* **[`agent.md`](agent.md):** Reglas operativas para agentes: estándar de código, manejo de commits, no usar Tailwind compilation pesada, preservar compatibilidad PWA.
* **[`task.md`](task.md):** Roadmap del proyecto, módulos implementados y backlog de tareas pendientes.
* **[`errors.md`](errors.md):** Registro histórico de errores resueltos (ej. drivers PostgreSQL, enums de SQLAlchemy, migraciones).
* **[`memory.md`](memory.md):** Bitácora detallada de sesiones anteriores y decisiones técnicas tomadas.

### Fase 3: Código Fuente
* **[`backend/main.py`](backend/main.py):** Punto de entrada FastAPI, enrutamiento según host/subdominio y servicio de archivos estáticos.
* **[`backend/routers/`](backend/routers/):** Endpoints REST divididos por dominio (`pos.py`, `kds.py`, `cashier.py`, `catalog.py`, `auth.py`, `inventory.py`).
* **[`backend/core/database.py`](backend/core/database.py):** Motor SQLAlchemy adaptativo con soporte `postgresql+psycopg2`.
* **[`backend/db/seed_recipes.py`](backend/db/seed_recipes.py):** Script de inicialización de datos demo (insumos reales, hamburguesas, boneless, bebidas, categorías y usuarios).
* **[`frontend/`](frontend/):** Interfaces HTML/JS independientes, responsivas y estilizadas con Tailwind vía CDN y Lucide Icons.

---

## 🚢 3. Dónde y Cómo se desplegó el Proyecto (Producción VPS)

GastroFlow está desplegado en el servidor VPS de producción con conexión SSH configurada bajo el alias `smartops`.

### Regla Crítica Anti-Conflicto:
En este VPS **ya existe otra instancia previa en producción** (`/opt/smartops/casino-erp`). Por tal motivo, **GastroFlow fue configurado con aislamiento absoluto** para no generar colisiones ni sobreescribir datos.

### Ficha Técnica de Despliegue en el VPS:
* **Host SSH:** `smartops`
* **Directorio en VPS:** `/opt/smartops/gastroflow`
* **Repositorio Git Oficial:** `https://github.com/emmiliotapia/gastroflow.git` (Rama `main`)
* **Archivo de Orquestación:** `docker-compose.gastroflow.yml`
* **Archivo de Variables:** `/opt/smartops/gastroflow/.env` (basado en `.env.gastroflow.example`)

### Mapeo de Recursos y Puertos:
| Recurso | GastroFlow (Activo) | Instancia Previa (`casino-erp`) | Estado |
| :--- | :--- | :--- | :--- |
| **Contenedor API Web** | `gastroflow_backend` | `casino_backend` | `Up` (Saludable) |
| **Contenedor Base de Datos** | `gastroflow_db` | `casino_db` | `Up` (Healthy) |
| **Red Bridge Docker** | `gastroflow_net` | `casino_net` | Aislada |
| **Volumen de Datos** | `gastroflow_pgdata` | `casino-erp_pgdata_casino` | Aislado |
| **Puerto Web / API Host** | **`8002`** (Interno: `8000`) | `8001` | **Libre y Verificado (200 OK)** |
| **Puerto PostgreSQL Host** | **`5441`** (Interno: `5432`) | `5434` | **Libre y Verificado** |

---

## 🛠️ 4. Cómo darle seguimiento al proyecto (Instrucciones Operativas)

### A. Para probar el sistema en local:
```bash
# 1. Ejecutar la suite completa de pruebas de integración:
python test_integration.py

# 2. Correr el backend en local (si se requiere depurar):
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### B. Para hacer cambios y subirlos a GitHub:
```bash
# Trabajar siempre en la rama main del repo gastroflow
git add .
git commit -m "feat(modulo): descripcion de la mejora"
git push gastroflow main
```

### C. Para desplegar actualizaciones en el VPS:
Conéctate por SSH y ejecuta la actualización sin tocar la otra instancia:
```bash
ssh smartops
cd /opt/smartops/gastroflow
git pull origin main
docker-compose -f docker-compose.gastroflow.yml restart backend
```

Si realizaste cambios en dependencias (`requirements.txt`) o Dockerfile:
```bash
docker-compose -f docker-compose.gastroflow.yml up -d --build backend
```

Para volver a poblar la base de datos de GastroFlow si se resetea:
```bash
docker-compose -f docker-compose.gastroflow.yml exec -T backend python -m backend.db.seed_recipes
```

### D. Para ver logs en el VPS:
```bash
docker logs gastroflow_backend -f --tail 50
docker logs gastroflow_db -f --tail 50
```

### E. Configuración en Nginx Proxy Manager (NPM):
Si deseas asignarle un subdominio público (ej. `gastroflow.smartopsia.com`):
* **Forward Host / IP:** `172.17.0.1` (o la IP del gateway Docker del host)
* **Forward Port:** `8002`
* **Websockets Support:** Activar obligatoriamente (requerido por el monitor KDS).
* **SSL:** Let's Encrypt con Force SSL activado.

---

## ⚠️ 5. Puntos de Atención y Trampas Comunes
1. **Nunca usar `docker-compose.yml` genérico en `/opt/smartops/gastroflow`:** Usa siempre `-f docker-compose.gastroflow.yml` para evitar chocar con los nombres `casino_backend` o puertos `8001/5434`.
2. **Driver de Base de Datos:** En `backend/core/database.py`, se asegura el prefijo `postgresql+psycopg2://` porque SQLAlchemy 2.0 por defecto busca `psycopg` (v3). No remover esta adaptación.
3. **Tipos Enum en PostgreSQL:** En `backend/models/ticket.py`, el enum `ticket_status_enum` debe conservar `create_type=True` para que PostgreSQL cree el tipo compuesto si se levanta una base de datos limpia.
4. **Enfoque Comercial del Frontend:** Mantener las descripciones de `index.html` orientadas a beneficios de negocio (rotación de mesas, control de mermas, cero papel) y no a jerga técnica de desarrollo.
