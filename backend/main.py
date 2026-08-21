"""
Punto de Entrada Principal - FastAPI Core Backend
================================================
Este módulo inicializa la aplicación FastAPI para el Casino Intelligent Hub,
configura middlewares, routers y el health check de infraestructura.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Casino Intelligent Hub - Core API",
    description="API REST modular para gestión de AyB, KDS, Tickets de Mantenimiento y Servidor MCP SmartOpsia.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuración CORS White-Label
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar Routers de la API
from backend.routers import auth, catalog, inventory
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(inventory.router)


@app.get("/", tags=["Root"])
def read_root():
    """
    Endpoint raíz de bienvenida.
    """
    return {
        "system": "Casino Intelligent Hub ERP",
        "status": "online",
        "version": "1.0.0"
    }


@app.get("/health", tags=["Healthcheck"])
def health_check():
    """
    Endpoint de comprobación de estado de infraestructura.
    """
    return {
        "status": "healthy",
        "services": {
            "api": "ok"
        }
    }
