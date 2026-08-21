/casino-erp-core
│
├── .env.example              # Variables de entorno base (DB, n8n webhooks, etc.)
├── agent.md                  # Reglas del agente y estándares de código
├── blueprint.md              # Documentación técnica y flujos de datos
├── task.md                   # Roadmap y tareas pendientes (Fases y submódulos)
├── memory.md                 # Historial de sesiones
├── errors.md                 # Registro de errores y soluciones
├── map.md                    # Topología del VPS y puertos
│
├── /config                   # <-- El corazón White-Label
│   ├── tenants.json          # Configuración por cliente/casino (nombre, logo, colores CSS, límites)
│   └── themes/               # Estilos personalizados (Obsidian & Gold, etc.)
│
├── /backend                  # API Principal (Python / FastAPI)
│   ├── /core                 # Configuración de BD, seguridad, JWT y middleware
│   ├── /models               # Modelos SQLAlchemy / ORM (Ingredientes, Recetas, Máquinas, Tickets)
│   ├── /schemas              # Esquemas Pydantic para validación de datos
│   ├── /routers              # Endpoints REST (ayb, kds, tickets, inventory, auth)
│   ├── /services             # Lógica de negocio pura (descuento de inventario, validación de PINs)
│   ├── /utils                # Helpers (conexión con n8n, disparadores de webhooks)
│   ├── Dockerfile
│   └── requirements.txt
│
├── /frontend                 # PWAs Ligeras (Vanilla JS / Tailwind o framework minimalista)
│   ├── /shared               # Componentes y estilos reutilizables (fetch wrapper, service workers)
│   ├── /pwa-client           # Portal del QR (Mini catálogo de AyB / Asistencia)
│   ├── /pwa-kds              # KDS para Cocina y Barra (Cambios de estado táctiles)
│   ├── /pwa-staff            # CRM de Tickets, escaneo rápido y panel de Jefes de Sala (PIN)
│   └── Dockerfile            # (O servidas estáticamente por Nginx)
│
└── /n8n                      # Exportaciones de workflows JSON (para respaldo y versionado)
    ├── ayb-notification-flow.json
    └── ticket-escalation-flow.json