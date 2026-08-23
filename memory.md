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

## Implementación de Portal de Caja y Cuentas Pendientes - 2026-08-21
- **Modelo de Cuentas y Cobros:** Añadida la enumeración `PaymentStatus` y los campos `payment_status` y `payment_method` a la cabecera del pedido `Order` para dar trazabilidad al cobro.
- **Automatización de Pago:** Las comandas creadas a $0.00 (100% cortesías por nivel o PIN) se registran automáticamente como `COMPLIMENTARY` con método de pago `COURTESY`. El resto inician en `PENDING` para su cobro definitivo en caja.
- **Router y API de Caja:** Creado `routers/cashier.py` para el listado FIFO de comandas pendientes de cobro y registro seguro de cobro (`CASH`/`CARD`/`COURTESY` con PIN de supervisor).
- **Portal de Caja / Barra:** Creado `frontend/cashier.html` con estética Obsidian & Gold para bartenders y cajeros de sala. Permite desglosar comandas activas por slot y realizar cobros parciales o cierres financieros de cuentas.

## Implementación de Menú Digital y PWA Cliente Anónimo - 2026-08-22
- **Portal de Clientes en Sala (`frontend/cliente.html`):** Desarrollado con estética Obsidian & Gold y usabilidad móvil táctil superior para jugadores en sala.
- **Acceso Cero Fricción:** Detección automática del identificador de máquina mediante parámetros de URL (`?machine_id=...`, `?slot=...`) sin requerir autenticación ni registro.
- **Sticky Cart Footer:** Barra inferior flotante fija verde esmeralda con contador de productos en tiempo real, total acumulado y botón "Enviar Pedido".
- **Garantía Transaccional y Sandboxing:** Las órdenes públicas se emiten con `current_user = None`, descuentan inventario de forma atómica en cocina o barra y emiten instantáneamente la comanda a KDS y al listado de cuentas abiertas de Caja.
- **Dock de Asistencia en Sala:** Botones discretos integrados para llamar mesero, solicitar recarga de saldo (Runners) y reportar fallas técnicas (Sistemas).
- **Enrutamiento Inteligente:** Mapeo automático de subdominios `menu.smartopsia.com` y `cliente.smartopsia.com` y rutas `/menu` y `/cliente`.

## Despliegue de Servidor Privado de Notificaciones Push (ntfy) - 2026-08-23
- **Contenedor Dedicado (`casino_ntfy`):** Integrada la imagen oficial `binwiederhier/ntfy` conectada a la red Docker `casino_net`.
- **Puerto y Mapeo Host:** Puerto host **`8080`** mapeado al puerto interno `80` del contenedor para balanceo por Nginx Proxy Manager.
- **Subdominio Configurado:** `https://ntfy.smartopsia.com` apuntando a `172.17.0.1:8080` (con WebSockets y SSL activados).
- **Persistencia y Control de Acceso:**
  - Archivo de configuración central: `docker/ntfy/server.yml`.
  - Base de datos SQLite persistente para mensajes y caché: `/var/cache/ntfy/cache.db`.
  - Base de datos de autenticación y tokens de seguridad: `/var/cache/ntfy/user.db`.
- **Topics Segregados Migrados al Servidor Privado:**
  - `https://ntfy.smartopsia.com/prestige-meseros` (Llamados de clientes y comida lista).
  - `https://ntfy.smartopsia.com/prestige-runners` (Solicitudes de recargas de créditos).
  - `https://ntfy.smartopsia.com/prestige-kds` (Nuevas comandas a cocina y barra).
  - `https://ntfy.smartopsia.com/prestige-sistemas` (Fallas técnicas en slots y tickets).
- **Scripts y n8n Actualizados:** `notify.sh`, `backend/utils/n8n.py` y `n8n_workflow_prestige.json` apuntan por defecto a `https://ntfy.smartopsia.com`.

## Cierre de Operación Restaurante & Suite de Pruebas E2E - 2026-08-23
- **Corte de Caja / Reporte Z (`GET /api/v1/cashier/corte-caja`):**
  - Módulo financiero para liquidar el turno con desglose segregado de ingresos (`CASH`, `CARD`, `COURTESY`).
  - Totalización de mermas y balance neto en caja (`Balance = Ventas - Mermas`).
  - Modal interactivo con opción de impresión en `frontend/cashier.html`.
- **Historial y Auditoría de Comandas (`GET /api/v1/cashier/history`):**
  - Permite auditar en tiempo real qué usuario emitió cada orden, en qué máquina/slot y el desglose de productos despachados con estado de pago.
- **Bitácora Gráfica de Mermas (`GET & POST /api/v1/inventory/waste`):**
  - Interfaz visual en `frontend/catalogo.html` para la bitácora de pérdidas valorizadas en Cocina/Barra, asegurando el descuento atómico de stock.
- **Suite de Pruebas Automatizadas End-to-End (`tests/test_restaurant_e2e.py`):**
  - Validación automatizada completa de Flujo 1 (Comanda QR -> KDS FIFO -> Cashier -> Pago Efectivo/Cortesía PIN -> Descuento atómico -> Arqueo Reporte Z).
  - Validación automatizada de Flujo 2 (Asistencia Runners `🟡 Pedir Saldo`, Meseros y Falla Técnica Sistemas hacia `ntfy`).
  - Validación de Flujo 3 (Merma valorizada y balance neto en corte de turno).
  - Validación de Flujo 4 (Idempotencia Anti-Double Tap, Cancelación con PIN y Reversa/Merma automática, Cierre Blindado con Arqueo de Efectivo).
  - Resultado: 100% de éxito en todas las pruebas.

## Seguros Operativos y Blindaje Transaccional - 2026-08-23
- **Idempotencia / Anti-Double Tap (`client_order_id`):**
  - Cada solicitud de comanda en `cliente.html`, `pos.html` y `cashier.html` envía un token único de cliente. Si la red o el usuario reintenta, el backend detecta el token existente y retorna la comanda ya procesada sin duplicar registros ni descontar stock múltiple.
- **Cancelaciones Auditadas con PIN (Poka-Yoke):**
  - Todo intento de cancelación exige obligatoriamente un `supervisor_pin` válido (`JEFE_DE_SALA` o `ADMIN`).
  - Si la comanda estaba en `PENDING` (no cocinada), se genera una reversa limpia al inventario.
  - Si la comanda estaba en `PREPARING`, `READY` o `DELIVERED`, se registra automáticamente una `WasteLog` (merma justificada) asociada al supervisor que autorizó.
- **Cierre Definitivo de Turno & Reporte Z Inmutable (`POST /api/v1/cashier/corte-caja/close`, modelo `ShiftClosing`):**
  - Genera un certificado inmutable (`CRTE-YYYYMMDD-XXXX`) registrando el arqueo físico declarado vs teórico calculado, diferencia monetaria (sobrante/faltante) y autorización mediante PIN.






