# 🧭 GastroFlow OS — Documento Guía de Continuidad (`resumen.md`)

> **Propósito:** Esta guía está diseñada para que cualquier agente de IA o desarrollador pueda tomar el proyecto, entenderlo en minutos y continuar su desarrollo o mantenimiento sin fricciones ni riesgos de colisión en producción.

---

## 📌 1. ¿Qué es GastroFlow OS y qué hace el proyecto?
**GastroFlow OS** es un ecosistema operativo y tecnológico modular para el sector gastronómico (restaurantes, bares, cafeterías y dark kitchens).
El sistema resuelve la desconexión operativa entre salón, cocina y administración a través de interfaces web ligeras (PWAs) sincronizadas en tiempo real:

1. **Menú Digital QR y Autopedidos (`frontend/cliente.html`):** Los clientes arman su pedido desde la mesa sin apps. Para blindar la cocina contra bromas o pedidos por error, la comanda entra en estado `PENDING_CONFIRMATION` y alerta al mesero para validarla a pie de mesa antes de encender fogones.
2. **Comandero Móvil Multifunción para Meseros (`frontend/pos.html`):** Terminal integral para smartphones/tablets con 4 vistas operativas:
   - **Levantar Comanda:** Botonera táctil rápida con notas e impresión de tickets térmicos 80mm.
   - **Cuentas de Mesa:** Listado en vivo de mesas ocupadas, desglose de cuentas, botón para **Cobrar/Cerrar** y botón para **Matar Cuenta** (cancelación segura con motivo y liberación inmediata de mesa).
   - **Validación de Pedidos QR:** Bandeja de entrada para revisar pedidos de clientes a pie de mesa, aprobarlos hacia cocina o rechazarlos.
   - **Corte de Turno:** Métricas en tiempo real de ventas cobradas, cuentas activas, comandas entregadas, ticket promedio e impresión de reporte Z en impresora térmica.
3. **Monitor KDS de Cocina y Barra (`frontend/kds.html`):** Pantalla en tiempo real conectada mediante triple vía (API REST, WebSockets `/api/v1/ws/kds` y Server-Sent Events de ntfy) que ordena las comandas en cola FIFO con semáforo de tiempos (Verde, Ámbar, Rojo +15m), alertas sonoras (`playBeep`) y botones para cambiar estado (`PREPARING`, `READY`, `DELIVERED`).
4. **Punto de Venta / Terminal de Caja (`frontend/cashier.html`):** Cobro multiformato (efectivo, tarjetas), división de cuentas entre comensales, control de propinas y arqueo ciego protegido por PIN.
5. **Escandallos y Fichas Técnicas (`frontend/catalogo.html`):** Control estricto del costo unitario por receta, margen bruto y deducción automática de insumos con cada venta.
6. **Consola de Alertas Operativas (`frontend/alerts.html`):** Transmisión y simulación de eventos de mesa lista, asistencia de meseros o platos demorados hacia el celular del personal vía webhooks y servidor push.
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
* **[`errors.md`](errors.md):** Registro histórico de errores resueltos (ej. drivers PostgreSQL, enums de SQLAlchemy, migraciones, endpoints alias de pedidos).
* **[`memory.md`](memory.md):** Bitácora detallada de sesiones anteriores y decisiones técnicas tomadas.

### Fase 3: Código Fuente Crítico
* **[`backend/main.py`](backend/main.py):** Punto de entrada FastAPI, enrutamiento según host/subdominio (`menu.*`, `pos.*`, `kds.*`, `caja.*`) y servicio de archivos estáticos.
* **[`backend/routers/kds.py`](backend/routers/kds.py):** Núcleo de comandas (`POST /api/v1/orders/`), listado KDS (`GET /api/v1/kds/orders`), actualización de estados (`PATCH /api/v1/kds/orders/{id}/status`), cancelación con PIN y canal WebSocket (`/api/v1/ws/kds`).
* **[`backend/routers/pos.py`](backend/routers/pos.py):** Configuración de botonera POS y alias `POST /api/v1/pos/order` para compatibilidad directa con los formularios frontend de pedidos.
* **[`backend/utils/n8n.py`](backend/utils/n8n.py):** Despachador asíncrono en pool de hilos (`ThreadPoolExecutor`) hacia n8n webhooks y push notifications en ntfy. Cuenta con User-Agent personalizado (`GastroFlow/1.0`) para evitar bloqueos de Cloudflare y difusión garantizada a topics `prestige-kds`, `prestige-meseros`, etc.
* **[`backend/core/database.py`](backend/core/database.py):** Motor SQLAlchemy adaptativo con soporte `postgresql+psycopg2`.
* **[`backend/db/seed_recipes.py`](backend/db/seed_recipes.py):** Script de inicialización de datos demo (insumos reales, hamburguesas, boneless, bebidas, categorías y usuarios).
* **[`frontend/kds.html`](frontend/kds.html):** Pantalla KDS con conexión triple en vivo: polling continuo de respaldo cada 4s, WebSocket `/api/v1/ws/kds` y Server-Sent Events a `https://ntfy.smartopsia.com/prestige-kds/sse`.
* **[`frontend/cliente.html`](frontend/cliente.html):** Menú cliente que envía pedidos a `/api/v1/pos/order`, emite eventos locales y envía push directo a `prestige-kds` y `prestige-meseros`.
* **[`frontend/pos.html`](frontend/pos.html):** Comandero táctil que envía pedidos al backend y emite alerta a `prestige-kds`.
* **[`frontend/notifications.js`](frontend/notifications.js):** Librería UI moderna de notificaciones `GastroNotify` (reemplazo estético de `alert`, `prompt` y `confirm` con toasts flotantes, modales glassmorphism, Web Audio sintetizado e iconos Lucide).

---

## 🚢 3. Dónde y Cómo se desplegó el Proyecto (Producción VPS)

GastroFlow está desplegado en el servidor VPS de producción con conexión SSH configurada bajo el alias `smartops`.

### Regla Crítica Anti-Conflicto:
En este VPS **ya existe otra instancia previa en producción** (`/opt/smartops/casino-erp`). Por tal motivo, **GastroFlow fue configurado con aislamiento absoluto** para no generar colisiones ni sobreescribir datos.

### Ficha Técnica de Despliegue en el VPS:
* **Host SSH:** `smartops`
* **Directorio en VPS:** `/opt/smartops/gastroflow`
* **Repositorios Git Oficiales:**
  - `gastroflow` -> `https://github.com/emmiliotapia/gastroflow.git` (Rama `main`)
  - `origin` -> `https://github.com/emmiliotapia/PRESTIGE.git` (Rama `main`)
* **Archivo de Orquestación:** `docker-compose.gastroflow.yml`
* **Archivo de Variables:** `/opt/smartops/gastroflow/.env`

### Mapeo de Recursos y Puertos:
| Recurso | GastroFlow (Activo) | Instancia Previa (`casino-erp`) | Estado |
| :--- | :--- | :--- | :--- |
| **Contenedor API Web** | `gastroflow_backend` | `casino_backend` | `Up` (Saludable) |
| **Contenedor Base de Datos** | `gastroflow_db` | `casino_db` | `Up` (Healthy) |
| **Red Bridge Docker** | `gastroflow_net` | `casino_net` | Aislada |
| **Volumen de Datos** | `gastroflow_pgdata` | `casino-erp_pgdata_casino` | Aislado |
| **Puerto Web / API Host** | **`8002`** (Interno: `8000`) | `8001` | **Libre y Verificado (200 OK)** |
| **Puerto PostgreSQL Host** | **`5441`** (Interno: `5432`) | `5434` | **Libre y Verificado** |
| **NTFY Server** | `https://ntfy.smartopsia.com` | `https://ntfy.smartopsia.com` | Compartido |
| **NTFY Topic KDS** | `prestige-kds` | `prestige-kds` | Verificado con Prioridad 5 |
| **NTFY Topic Meseros** | `prestige-meseros` | `prestige-meseros` | Verificado |

---

## 🔔 4. Arquitectura del Flujo de Notificaciones y KDS en Vivo

El flujo de una orden desde cualquier módulo hasta la cocina y los dispositivos del personal funciona de la siguiente manera:

```
[Cliente QR / POS]
       │
       ├─► 1. POST /api/v1/pos/order (Backend FastAPI en :8002)
       │       │
       │       ├─► Crea orden transaccional en PostgreSQL (`gastroflow_db`)
       │       ├─► Descuenta inventario de insumos (recetas/escandallos)
       │       ├─► Emite WebSocket a clientes conectados (`/api/v1/ws/kds`)
       │       └─► `trigger_order_webhook`:
       │               ├─► POST n8n webhook (`https://n8n.smartopsia.com/webhook/ordenes-nuevas`)
       │               └─► POST HTTP a `https://ntfy.smartopsia.com` con topics:
       │                       - `prestige-kds` (Prioridad 5, tags: fire, cooking)
       │                       - `prestige-comandas`
       │
       ├─► 2. Respaldo directo de navegador:
       │       └─► POST `https://ntfy.smartopsia.com/prestige-kds` (Prioridad Urgent)
       │
       └─► 3. Pantalla KDS (`frontend/kds.html`):
               ├─► Recibe evento WebSocket instantáneo
               ├─► Recibe evento Server-Sent Events (SSE) de ntfy
               ├─► Ejecuta `fetchOrdersFromAPI()` cada 4s
               ├─► Emite sonido de alerta acústica (`playBeep()`)
               └─► Renderiza la tarjeta con temporizador FIFO y mesa
```

---

## 🛠️ 5. Cómo darle seguimiento al proyecto (Instrucciones Operativas)

### A. Para probar el sistema en local:
```bash
# 1. Ejecutar la suite completa de pruebas de integración:
python test_integration.py

# 2. Correr el backend en local (si se requiere depurar):
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### B. Para hacer cambios y subirlos a GitHub:
Trabajar localmente y sincronizar en ambos remotos:
```bash
git add .
git commit -m "feat(modulo): descripcion de la mejora"
git push origin main
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
# Ver logs del backend de GastroFlow en tiempo real:
ssh smartops "docker logs gastroflow_backend -f --tail 50"

# Ver logs de la base de datos:
ssh smartops "docker logs gastroflow_db -f --tail 50"
```

### E. Para verificar alertas de ntfy directamente en terminal:
```bash
# Consultar los últimos 5 mensajes en el canal de cocina:
ssh smartops "curl -s -H 'User-Agent: GastroFlow/1.0' 'https://ntfy.smartopsia.com/prestige-kds/json?poll=1&limit=5'"
```

### F. Configuración en Nginx Proxy Manager (NPM):
Para publicar subdominios en el reverse proxy NPM del VPS:
* **Forward Host / IP:** `172.17.0.1` (o la IP del gateway Docker del host VPS)
* **Forward Port:** `8002`
* **Websockets Support:** **Activar obligatoriamente** (requerido por el monitor KDS en `/api/v1/ws/kds`).
* **SSL:** Let's Encrypt con Force SSL activado.

---

## ⚠️ 6. Puntos de Atención y Trampas Comunes
1. **Nunca usar `docker-compose.yml` genérico en `/opt/smartops/gastroflow`:** Usa siempre `-f docker-compose.gastroflow.yml` para evitar chocar con los nombres `casino_backend` o puertos `8001/5434`.
2. **User-Agent en llamados a ntfy:** Cloudflare bloquea peticiones de Python con `Python-urllib` (Error 1010). Siempre incluir `User-Agent: GastroFlow/1.0` en cualquier petición HTTP saliente.
3. **Prefijo de NTFY en .env:** La variable `NTFY_TOPIC_PREFIX` en `/opt/smartops/gastroflow/.env` debe estar fijada en `prestige-` para que coincida con las suscripciones móviles de los supervisores y cocineros (`prestige-kds`, `prestige-meseros`).
4. **Driver de Base de Datos:** En `backend/core/database.py`, se asegura el prefijo `postgresql+psycopg2://` porque SQLAlchemy 2.0 por defecto busca `psycopg` (v3). No remover esta adaptación.
5. **Tipos Enum en PostgreSQL:** En `backend/models/ticket.py`, el enum `ticket_status_enum` debe conservar `create_type=True` para que PostgreSQL cree el tipo compuesto si se levanta una base de datos limpia.
6. **Enfoque Comercial del Frontend:** Mantener las descripciones de `index.html` orientadas a beneficios de negocio (rotación de mesas, control de mermas, cero papel) y no a jerga técnica de desarrollo.
