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
