# Reglas del Agente y Estándares de Código (`agent.md`)

## 1. Reglas de Oro del Proyecto
1. **TODO CÓDIGO DEBE ESTAR DOCUMENTADO Y COMENTADO:**
   - Docstrings descriptivos en todas las funciones, métodos y clases.
   - Tipado estricto en Python (FastAPI / Pydantic / SQLAlchemy 2.0).
   - Comentarios explicativos detallados en bloques de lógica complejos o reglas de negocio críticas (descuento de inventario, validaciones de seguridad Poka-Yoke, etc.).

2. **ARQUITECTURA MODULAR ("METALEGO"):**
   - Separación limpia entre Core Backend (`/backend`), la capa de personalización White-Label (`/config/tenants.json`) y las interfaces PWA ligeras (`/frontend`).
   - El backend debe ser agnóstico de branding y 100% reutilizable.

3. **SEGURIDAD, ESTADOS Y ROLES:**
   - Validación estricta en backend de roles (`ADMIN`, `JEFE_DE_SALA`, `MESERO`, `COCINA`, `BARRA`, `SISTEMAS`, `CLIENTE`).
   - Control explícito de estados permitidos (`pendiente`, `en proceso`, `hold`, `finalizado`).
   - Firmas digitales / PINs cifrados (Poka-Yoke) para aprobaciones críticas de Jefes de Sala.
