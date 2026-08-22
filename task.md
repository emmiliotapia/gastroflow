# Roadmap de Tareas - Casino ERP (`task.md`)

## Fase 1: Cimientos y Base de Datos (Core Backend)
- [x] Configurar estructura inicial del repositorio y archivos de control.
- [x] Diseñar el modelo de base de datos relacional (Ingredientes, Subrecetas, Productos AyB).
- [x] Diseñar el modelo de Máquinas, Usuarios, Roles y PINs.
- [x] Habilitar extensión `pgvector` en PostgreSQL (`CREATE EXTENSION IF NOT EXISTS vector;`) y script de arranque Docker.
- [x] Levantar configuración de Docker Compose aislado, `.env.example`, `deploy.sh` e infraestructura VPS.

## Fase 2: Módulos Core, Lógica de Negocio y Reglas
- [x] **Módulo de Autenticación y RBAC (ACLs):**
  - [x] Implementar autenticación JWT y hashing de contraseñas con Passlib/Bcrypt.
  - [x] Implementar middleware y dependencias de autorización de roles (`ADMIN`, `JEFE_DE_SALA`, `WAITER`, `SISTEMAS`, etc.).
  - [x] Implementar middleware de validación del NIP/PIN numérico (`hashed_pin`) para supervisores (Poka-Yoke).
- [x] **Módulo CRUD de Catálogos:**
  - [x] Endpoints FastAPI para gestión completa (Crear, Leer, Actualizar, Desactivar) de Ingredientes y Unidades de Medida.
  - [x] Endpoints FastAPI para gestión completa de Productos de AyB (Preparados vs Directos).
  - [x] Endpoints FastAPI para gestión de Recetas y vinculación de insumos.
  - [x] Endpoints FastAPI para gestión de Máquinas / Slots y generación de tokens de QR.
- [x] **Módulo de Lógica de Inventario y Operación:**
  - [x] Implementar modelos de datos y endpoints para gestión de stock por bodegas (`WAREHOUSE`, `KITCHEN`, `BAR`).
  - [x] Implementar módulo de porcionado y conversión de insumos macro a micro.
  - [x] Implementar módulo de registro y valorización monetaria de mermas y desperdicios.
  - [x] Implementar motor de descuento automático y atómico de inventario por comanda POS (Cocina vs Barra).
  - [x] Implementar servicio de alertas de stock mínimo con sugerencia de compras para n8n/notify.sh.
  - [x] Implementar modelos de datos y endpoints para configuración visual de botonera del POS (`POSCategory` / `POSButton`).
  - [x] Implementar modelos y endpoints para cobro/comanda de pedidos (`Order` / `OrderItem`), integrados de forma transaccional y atómica al descuento de inventario.
  - [x] Implementar endpoints KDS para listar comandas FIFO por estación y actualizar estados.
  - [x] Implementar gestor de WebSockets (`kds_manager`) para notificaciones en tiempo real a pantallas de Cocina y Barra.
  - [x] Implementar validación de niveles de clientes y sistema de cortesías con NIP.
  - [x] Crear endpoints de tickets de sistemas con los 4 estados (`PENDIENTE`, `EN_PROCESO`, `HOLD`, `FINALIZADO`).
  - [x] Crear endpoints de Caja y Control de Cuentas Pendientes (`cashier.py`).

## Fase 3: Automatizaciones y Sistema Nervioso (n8n)
- [x] Configurar webhooks en FastAPI hacia n8n.
- [x] Integrar canales de `notify.sh` segregados (Meseros, Runners, Sistemas, Alertas).
- [ ] Configurar cron job de escalamiento para minutas y tickets vencidos.

## Fase 4: Interfaces y PWAs (Capas Visibles)
- [x] Desarrollar PWA Cliente / Portal Público (`cliente.html`) con acceso cero fricción por QR (`?machine_id=...`), Sticky Cart Footer y Dock de Asistencia.
- [x] Desarrollar PWA Comandero Meseros (`pos.html`) con selector lateral de Venta vs Cortesía VIP y escáner de QR.
- [x] Desarrollar PWA KDS (`kds.html`) (Pantalla táctil de cocina/barra, conexión WebSocket con semáforo de tiempos y timbres sonoros).
- [x] Implementar infraestructura PWA (`manifest.json` y Service Worker `sw.js` para modo offline/standalone).
- [x] Desarrollar PWA Staff (`staff.html`) (Tickets de sistemas y autorización por PIN).
- [x] Desarrollar Portal de Caja / Barra (`cashier.html`).
- [x] Desarrollar Centro de Catálogo y Fichas Técnicas (`catalogo.html`).
- [x] Desarrollar Launchpad Central de Módulos (`index.html`).


## Fase 5: Inteligencia Artificial, RAG y Servidor MCP SmartOpsia
- [ ] Diseñar modelos ORM para almacenamiento de Embeddings Vectoriales (Manuales, Tickets, Minutas) usando `pgvector`.
- [ ] Crear pipeline de vectorización de documentos y motor de Búsqueda Híbrida (SQL + Coseno Vectorial).
- [ ] Construir Servidor MCP (Model Context Protocol) para SmartOpsia Agent.
- [ ] Implementar motor de consultas NL-to-SQL con validación estricta de ACLs/Roles por usuario.
- [ ] Desarrollar generador automatizado de reportes ejecutivos e insights en lenguaje natural.