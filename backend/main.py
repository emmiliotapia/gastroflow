"""
Punto de Entrada Principal - FastAPI Core Backend
================================================
Este módulo inicializa la aplicación FastAPI para el Casino Intelligent Hub,
configura middlewares, routers y el health check de infraestructura.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
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



from fastapi.responses import FileResponse, RedirectResponse

@app.get("/", tags=["Root"])
def read_root(request: Request):
    """
    Sirve la interfaz adecuada según el subdominio o el Launchpad principal.
    - menu.smartopsia.com / cliente.smartopsia.com -> cliente.html (Menú público para jugadores)
    - pos.smartopsia.com -> pos.html (Comandero meseros)
    - kds.smartopsia.com -> kds.html (Cocina / Barra)
    - caja.smartopsia.com / cashier.smartopsia.com -> cashier.html
    - cocina.smartopsia.com / catalogo.smartopsia.com -> catalogo.html
    - Cualquier otro host / raíz general -> index.html (Launchpad)
    """
    host = request.headers.get("host", "").lower().split(":")[0]
    
    if (host.startswith("menu.") or host.startswith("cliente.")) and os.path.exists("frontend/cliente.html"):
        return FileResponse("frontend/cliente.html")
    if host.startswith("pos.") and os.path.exists("frontend/pos.html"):
        return FileResponse("frontend/pos.html")
    if host.startswith("kds.") and os.path.exists("frontend/kds.html"):
        return FileResponse("frontend/kds.html")
    if (host.startswith("caja.") or host.startswith("cashier.")) and os.path.exists("frontend/cashier.html"):
        return FileResponse("frontend/cashier.html")
    if (host.startswith("cocina.") or host.startswith("catalogo.")) and os.path.exists("frontend/catalogo.html"):
        return FileResponse("frontend/catalogo.html")
    if host.startswith("staff.") and os.path.exists("frontend/staff.html"):
        return FileResponse("frontend/staff.html")

    if os.path.exists("frontend/index.html"):
        return FileResponse("frontend/index.html")
    return RedirectResponse(url="/frontend/index.html")


@app.get("/cliente", tags=["Frontend Layouts"])
@app.get("/menu", tags=["Frontend Layouts"])
def get_client_menu_page():
    """Sirve el Menú Digital y Portal de Pedidos para Clientes en Sala."""
    return FileResponse("frontend/cliente.html") if os.path.exists("frontend/cliente.html") else RedirectResponse("/frontend/cliente.html")

@app.get("/pos", tags=["Frontend Layouts"])
def get_pos_page():
    """Redirige directamente al Comandero Móvil POS."""
    return FileResponse("frontend/pos.html") if os.path.exists("frontend/pos.html") else RedirectResponse("/frontend/pos.html")

@app.get("/kds", tags=["Frontend Layouts"])
def get_kds_page():
    """Redirige directamente a la pantalla KDS de Cocina y Barra."""
    return FileResponse("frontend/kds.html") if os.path.exists("frontend/kds.html") else RedirectResponse("/frontend/kds.html")

@app.get("/cashier", tags=["Frontend Layouts"])
@app.get("/caja", tags=["Frontend Layouts"])
def get_cashier_page():
    """Redirige directamente al POS de Caja y Barra."""
    return FileResponse("frontend/cashier.html") if os.path.exists("frontend/cashier.html") else RedirectResponse("/frontend/cashier.html")

@app.get("/catalogo", tags=["Frontend Layouts"])
@app.get("/cocina", tags=["Frontend Layouts"])
def get_catalogo_page():
    """Redirige directamente al Centro de Catálogo y Fichas Técnicas de Cocina."""
    return FileResponse("frontend/catalogo.html") if os.path.exists("frontend/catalogo.html") else RedirectResponse("/frontend/catalogo.html")


@app.get("/staff", tags=["Frontend Layouts"])
def get_staff_page():
    """Redirige directamente al Panel de Staff y Supervisión."""
    return FileResponse("frontend/staff.html") if os.path.exists("frontend/staff.html") else RedirectResponse("/frontend/staff.html")



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
