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

### Funcionalidades Clave del Servidor MCP:
- **Interpretación de Intención y NL-to-SQL:** Traduce preguntas en lenguaje natural ("¿Cuál fue la bebida más solicitada en la Zona VIP el fin de semana?") a consultas SQL optimizadas.
- **Control Estricto de Seguridad y ACLs:** Garantiza que el agente solo consulte tablas y métricas autorizadas según el rol del usuario que realiza la petición (`ADMIN`, `JEFE_DE_SALA`, `TECHNICIAN`), impidiendo inyecciones o escalación de privilegios.
- **Búsqueda Híbrida (Hybrid Search):** Combina agregaciones SQL tradicionales (`SUM`, `COUNT`, `AVG`) con similitud de coseno vectorial (`<->`) para correlacionar datos numéricos con contexto no estructurado.
- **Generación Automatizada de Reportes:** Genera informes ejecutivos en formato Markdown y JSON con análisis predictivo de mermas de AyB y tiempos promedio de resolución de tickets.