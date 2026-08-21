# Blueprint del Ecosistema - Casino ERP & Smart Hub

## 1. Visión General
Sistema modular de gestión operativa para casino enfocado en control de inventarios de AyB, POS móvil mediante QR inteligente, KDS en tiempo real, gestión de tickets de sistemas/mantenimiento, automatizaciones mediante n8n, y capacidades nativas de Inteligencia Artificial (RAG con `pgvector` y Agente Inteligente SmartOpsia mediante MCP).

---

## 2. Estrategia White-Label
La capa visual y las reglas específicas del recinto se configuran a través de `/config/tenants.json`. El código fuente (Core) es agnóstico y reutilizable para cualquier ubicación, adaptando branding (colores, logotipos) y umbrales de negocio de manera dinámica.

---

## 3. Flujo de Datos Crítico

1. **QR Scan:** Lee `?machine_id=X`. La PWA detecta rol (Cliente vs Staff).
2. **Cliente (AyB):** Selecciona productos -> Valida nivel/cortesía -> Si excede, solicita PIN de Jefe de Sala -> Webhook a n8n -> Actualiza stock en BD -> Dispara KDS y alerta a meseros/runners.
3. **Staff (Sistemas):** Abre ticket en blanco ligado al `machine_id` -> Inicia cronómetro -> Alerta a técnicos -> Cierre con Poka-Yoke (PIN obligatorio de Jefe de Sala).
4. **SmartOpsia Agent (IA & MCP):** Solicitud en lenguaje natural -> Consulta segura vía MCP -> Búsqueda Híbrida (SQL Relacional + Búsqueda Vectorial RAG) -> Generación automatizada de reportes ejecutivos y diagnóstico de mantenimiento.

---

## 4. Capa Nativa de IA & RAG con `pgvector`

El ecosistema utiliza **PostgreSQL** como motor unificado **Relacional y Vectorial** mediante la extensión `pgvector`. Esto elimina la necesidad de bases de datos vectoriales externas independientes y garantiza la consistencia transaccional ACID.

### Áreas de Indexación Vectorial (Embeddings):
1. **Histórico de Tickets de Sistemas:** Soluciones previas, diagnósticos de errores en tragamonedas (slots) y patrones de fallas recurrentes.
2. **Manuales Técnicos de Máquinas:** Documentación oficial por modelo (Bally, IGT, Aristocrat, etc.) indexada mediante chunks vectoriales para consulta rápida en sala.
3. **Minutas y Bitácora Operativa:** Registro semántico de juntas diarias, incidentes de seguridad y notas de turno de Jefes de Sala.

---

## 5. Arquitectura del Servidor MCP (Model Context Protocol) & Agente SmartOpsia

El Agente **SmartOpsia** interactúa con el Core Backend a través de un **Servidor MCP nativo**, actuando como el co-piloto analítico del casino.

```
┌─────────────────────────────────────────────────────────┐
│                 SmartOpsia Agent (LLM)                  │
└────────────────────────────┬────────────────────────────┘
                             │ Model Context Protocol (MCP)
                             ▼
┌─────────────────────────────────────────────────────────┐
│             MCP Server / Gateway (FastAPI)              │
│  - Parser de Intención (Lenguaje Natural)               │
│  - Validador Estricto de Seguridad y ACLs por Rol       │
└──────────────┬───────────────────────────┬──────────────┘
               │ Consulta SQL Relacional   │ Búsqueda Vectorial (RAG)
               ▼                           ▼
┌─────────────────────────────────────────────────────────┐
│             PostgreSQL (Relacional + pgvector)          │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Motor de Inventarios, Porcionado, Mermas y Descuento Atómico POS

El módulo de inventario (`/backend/services/inventory_service.py`) gestiona las existencias físicas en tiempo real segmentando bodegas y estaciones de consumo:

1. **Segmentación Multibodega (`StockLocation`)**:
   - `WAREHOUSE`: Almacén central de compras a proveedores.
   - `KITCHEN`: Estación de producción de platillos calientes y fríos.
   - `BAR`: Estación de bebidas y coctelería.

2. **Motor Atómico de Descuento POS (`deduct_product_stock`)**:
   - Para productos de venta directa (`DIRECT`): Descuenta la cantidad consumida directamente en la barra/estación.
   - Para productos preparados (`PREPARED`): Consulta la ficha técnica (`RecipeItem`) y descuenta de manera atómica la cantidad proporcional de cada insumo en la cocina o barra.

3. **Porcionado e Insumos Macro/Micro**:
   - Permite registrar la conversión de materia prima mayorista (ej. 1 KG de Carne Sirloin) en unidades dosificadas para la línea de cocina (ej. 5 porciones de 200g).

4. **Gestión y Valorización de Mermas (`WasteLog`)**:
   - Registra desperdicios con justificación explícita y deduce automáticamente el costo monetario perdido multiplicando la cantidad mermada por el costo unitario vigente del insumo.

5. **Alertas de Reabastecimiento Automático**:
   - Insumos por debajo de `minimum_stock` generan automáticamente registros estructurados de compras sugeridas para su enrutamiento mediante n8n / `notify.sh`.

---

## 7. Módulo POS, Comandas, KDS y WebSockets en Tiempo Real

Para dar soporte a la operación ágil y sin fricciones en sala, el sistema integra la siguiente arquitectura de comandas y despliegue:

1. **Botonera Dinámica del POS (`POSCategory` / `POSButton`)**:
   - Permite configurar categorías temáticas (pestañas) y botones físicos (con colores de aviso, orden e icono) asociados a productos. Facilita la carga rápida en tablets de meseros o el autoservicio desde códigos QR.

2. **Flujo y Ciclo de Vida de Comandas (`Order` / `OrderItem`)**:
   - Asocia pedidos a máquinas (`machine_id`) y empleados creadores.
   - Estados: `PENDING` -> `PREPARING` -> `READY` -> `DELIVERED`.
   - **Garantía Transaccional**: La creación de una orden abre un bloque atómico de base de datos. Si falla el descuento de stock de algún ingrediente de la receta en `deduct_product_stock`, se aborta la transacción (`rollback`) y no se crea la orden, garantizando la consistencia del inventario.

3. **Kitchen Display System (KDS)**:
   - Filtra órdenes en base a la estación de producción (`KITCHEN` o `BAR`) ordenándolas cronológicamente (FIFO) en tarjetas táctiles para optimizar los tiempos de despacho.

4. **Notificaciones Push en Tiempo Real (WebSockets KDS)**:
   - Administrado por `KDSConnectionManager`. Al crearse un pedido o cambiar de estado, se propaga un broadcast instantáneo a través de `/ws/kds` para actualizar de inmediato las pantallas activas de cocina o barra.