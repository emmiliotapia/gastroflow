# Historial de Sesiones y Contexto (`memory.md`)

## Sesión Inicial - 2026-08-20
- **Visión General:** Definido el ecosistema Casino Intelligent Hub (ERP Modular White-Label).
- **Flujo de Datos QR:** Escaneo `?machine_id=X` canaliza hacia Cliente (AyB) o Staff (Tickets Sistemas).
- **Fase Actual:** Fase 1 - Cimientos y Base de Datos (Core Backend).
- **Modelos BD Implementados (SQLAlchemy 2.0):**
  - `Ingredient` (`ingredients`) con unidades de medida (`UnitOfMeasure`).
  - `Product` y `RecipeItem` (`products`, `recipe_items`) diferenciando `PREPARED` vs `DIRECT` y estación `KDSStation`.
  - `Machine` (`machines`) con número de serie, activo, zona y token de QR.
  - `User` y `Role` (`users`, `roles`) con RBAC en JSON y `hashed_pin` opcional para Poka-Yoke.

## Actualización de Arquitectura de IA (pgvector & MCP) - 2026-08-20
- **Capa RAG con `pgvector`:** PostgreSQL operará como BD híbrida (Relacional + Vectorial) para indexar tickets de soporte, manuales de slots y minutas de juntas.
- **Servidor MCP SmartOpsia Agent:** Definida la arquitectura del gateway MCP para interpretación en lenguaje natural, consultas NL-to-SQL con seguridad ACL y generación automática de reportes.
- **Roadmap Actualizado (`task.md`):** Incluida tarea para extensión `pgvector` en Fase 1 y Fase 5 dedicada para el Agente MCP SmartOpsia.

## Implementación de Inventario, Seguridad y Despliegue en VPS - 2026-08-20
- **Autenticación & RBAC:** Implementados JWT, hashing Bcrypt de contraseñas y NIP/PIN de Jefes de Sala (Poka-Yoke).
- **Catálogos y Fichas Técnicas:** CRUD de Insumos, Productos y cálculo de ganancias de Recetas.
- **Inventarios y POS:** Módulo de stock por bodegas, mermas valorizadas, porcionado y descuento atómico del POS.
- **Despliegue en VPS (SmartOps) Completado:**
  - PostgreSQL levantado en puerto host **`5434`** y FastAPI en puerto **`8001`**.
  - Seeder pobló roles, usuarios, 36 insumos y 8 recetas de AyB.

## Desarrollo del Frontend PWA (POS & KDS) - 2026-08-20
- **Infraestructura PWA:** Creados `manifest.json` y Service Worker `sw.js` para caché offline bajo estética premium Obsidian & Gold.
- **pos.html:** Interfaz del comandero con carrito, panel de rejilla táctil dinámica y lectura de parámetro de URL `?machine_id=...` para slots.
- **kds.html:** Pantalla táctil FIFO para cocina/barra con conexión persistente WebSocket y reconexión exponencial.
- **Servicio Estático Integrado:** Los archivos estáticos se montaron a través de FastAPI en la ruta `/frontend/` y ya se encuentran desplegados y probados en el puerto `8001` del VPS.

## Implementación de Máquinas, Tickets, Cortesías y PWA Staff - 2026-08-21
- **Modelo de Datos y Seguridad:** Añadida la columna `membership_tier` a `User`, e implementado el modelo `Ticket` para seguimiento de incidencias técnicas en sala.
- **Validación de Cortesías y PIN Poka-Yoke:**
  - El endpoint de creación de comandas (`/api/v1/orders/`) ahora comprueba automáticamente los niveles de membresía (`CLASSIC` < `GOLD` < `PLATINUM` < `VIP`) contra el `courtesy_tier_min` de cada producto.
  - Se añadió la capacidad de sobreescribir cobros de cortesías insuficientes suministrando un `supervisor_pin` en el payload de creación de comanda.
- **CRUD y Routers REST:** Creados los routers para Máquinas (`/api/v1/machines`) y Tickets (`/api/v1/tickets`), implementando el flujo de estados (`PENDIENTE` -> `EN_PROCESO` -> `HOLD` -> `FINALIZADO`) y cierre estricto mediante PIN.
- **PWA Staff y Control Técnico:** Diseñada la interfaz `staff.html` con estética premium Obsidian & Gold, incluyendo listado interactivo de tragamonedas con generación de etiquetas QR, gestor de tickets FIFO y teclado numérico virtual para validación de PIN de supervisores en el cierre.
- **Integraciones n8n:** Añadido despachador de webhooks asíncrono no bloqueante en `backend/utils/n8n.py`.

