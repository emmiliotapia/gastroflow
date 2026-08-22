"""
Punto de Entrada Principal - FastAPI Core Backend
================================================
Este módulo inicializa la aplicación FastAPI para el Casino Intelligent Hub,
configura middlewares, routers y el health check de infraestructura.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from backend.websockets.kds_manager import kds_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializar el loop de asyncio en el connection manager de KDS
    loop = asyncio.get_running_loop()
    kds_manager.set_loop(loop)
    yield

app = FastAPI(
    title="Casino Intelligent Hub - Core API",
    description="API REST modular para gestión de AyB, KDS, Tickets de Mantenimiento y Servidor MCP SmartOpsia.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
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
from backend.routers import auth, catalog, inventory, pos, kds, machines, tickets, cashier
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(inventory.router)
app.include_router(pos.router)
app.include_router(kds.router)
app.include_router(machines.router)
app.include_router(tickets.router)
app.include_router(cashier.router)

# Servir PWA Estática y Fotografías de Productos
from fastapi.staticfiles import StaticFiles
import os

if os.path.exists("frontend"):
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

os.makedirs("uploads/products", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")



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


# --- ALIAS DE AUTENTICACIÓN ---
from fastapi import Request
from backend.schemas.auth import TokenResponse
from backend.routers.auth import login as auth_login
from backend.core.deps import get_db

@app.post("/login", response_model=TokenResponse, tags=["Autenticación"])
async def login_alias(request: Request, db = Depends(get_db)):
    """
    Alias global de inicio de sesión (/login) compatible con todos los frontends.
    """
    return await auth_login(request, db)
