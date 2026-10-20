"""
Punto de Entrada Principal - FastAPI Core Backend
================================================
Este módulo inicializa la aplicación FastAPI para GastroFlow,
configura middlewares, routers y el health check de infraestructura.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.websockets.kds_manager import kds_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-parchear y asegurar esquema de BD (creación de tablas/columnas nuevas)
    try:
        from backend.core.database import auto_patch_schema
        auto_patch_schema()
    except Exception as e:
        print(f"[STARTUP] Error auto-parcheando esquema de BD: {e}")

    # Inicializar el loop de asyncio en el connection manager de KDS
    loop = asyncio.get_running_loop()
    kds_manager.set_loop(loop)
    yield


app = FastAPI(
    title="GastroFlow - Core API",
    description="API REST modular para gestión de AyB, KDS, Tickets de Mantenimiento y Servidor MCP SmartOpsia.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# Configuración CORS: orígenes explícitos + regex de subdominios (definidos en .env)
from backend.core.config import settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
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

def _get_html_file(filename: str):
    """Localiza el archivo HTML de forma robusta en local o dentro del contenedor Docker."""
    candidates = [
        os.path.join("frontend", filename),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", filename),
        os.path.join("/app", "frontend", filename)
    ]
    for p in candidates:
        if os.path.exists(p):
            return FileResponse(p)
    return RedirectResponse(url=f"/frontend/{filename}")


@app.get("/", tags=["Root"])
def read_root(request: Request):
    """
    Sirve la interfaz adecuada según el subdominio o el Launchpad principal.
    - menu.smartopsia.com / cliente.smartopsia.com -> cliente.html (Menú público para jugadores)
    - pos.smartopsia.com -> pos.html (Comandero meseros)
    - kds.smartopsia.com -> kds.html (Cocina / Barra)
    - caja.smartopsia.com / cashier.smartopsia.com -> cashier.html
    - cocina.smartopsia.com / catalogo.smartopsia.com -> catalogo.html
    - Cualquier otro host (ej. prestige.smartopsia.com) -> index.html (Launchpad)
    """
    host = request.headers.get("host", "").lower().split(":")[0]
    
    if host.startswith("menu.") or host.startswith("cliente."):
        return _get_html_file("cliente.html")
    if host.startswith("pos."):
        return _get_html_file("pos.html")
    if host.startswith("kds."):
        return _get_html_file("kds.html")
    if host.startswith("caja.") or host.startswith("cashier."):
        return _get_html_file("cashier.html")
    if host.startswith("cocina.") or host.startswith("catalogo."):
        return _get_html_file("catalogo.html")
    if host.startswith("staff."):
        return _get_html_file("staff.html")

    return _get_html_file("index.html")


@app.get("/cliente", tags=["Frontend Layouts"])
@app.get("/cliente.html", tags=["Frontend Layouts"])
@app.get("/menu", tags=["Frontend Layouts"])
def get_client_menu_page():
    """Sirve el Menú Digital y Portal de Pedidos para Clientes en Sala."""
    return _get_html_file("cliente.html")

@app.get("/pos", tags=["Frontend Layouts"])
@app.get("/pos.html", tags=["Frontend Layouts"])
def get_pos_page():
    """Redirige directamente al Comandero Móvil POS."""
    return _get_html_file("pos.html")

@app.get("/kds", tags=["Frontend Layouts"])
@app.get("/kds.html", tags=["Frontend Layouts"])
def get_kds_page():
    """Redirige directamente a la pantalla KDS de Cocina y Barra."""
    return _get_html_file("kds.html")

@app.get("/cashier", tags=["Frontend Layouts"])
@app.get("/cashier.html", tags=["Frontend Layouts"])
@app.get("/caja", tags=["Frontend Layouts"])
def get_cashier_page():
    """Redirige directamente al POS de Caja y Barra."""
    return _get_html_file("cashier.html")

@app.get("/catalogo", tags=["Frontend Layouts"])
@app.get("/catalogo.html", tags=["Frontend Layouts"])
@app.get("/cocina", tags=["Frontend Layouts"])
def get_catalogo_page():
    """Redirige directamente al Centro de Catálogo y Fichas Técnicas de Cocina."""
    return _get_html_file("catalogo.html")

@app.get("/staff", tags=["Frontend Layouts"])
@app.get("/staff.html", tags=["Frontend Layouts"])
def get_staff_page():
    """Redirige directamente al Panel de Staff y Supervisión."""
    return _get_html_file("staff.html")

@app.get("/alerts", tags=["Frontend Layouts"])
@app.get("/alerts.html", tags=["Frontend Layouts"])
def get_alerts_page():
    """Redirige directamente al Panel de Alertas y Notificaciones."""
    return _get_html_file("alerts.html")

@app.get("/index.html", tags=["Frontend Layouts"])
def get_index_page():
    """Sirve el Launchpad principal directamente."""
    return _get_html_file("index.html")


@app.get("/manifest.json", include_in_schema=False)
def get_manifest():
    """Sirve el manifiesto PWA desde la raíz (las páginas lo referencian con ruta relativa)."""
    return _get_html_file("manifest.json")


@app.get("/sw.js", include_in_schema=False)
def get_service_worker():
    """Sirve el Service Worker desde la raíz para que su scope cubra todo el sitio."""
    return _get_html_file("sw.js")




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


from fastapi.responses import Response

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


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

