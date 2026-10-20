"""
Módulo de Conexión a la Base de Datos SQLAlchemy
================================================
Este módulo inicializa el motor de base de datos (Engine) y la fábrica de sesiones (sessionmaker)
para PostgreSQL, ofreciendo una gestión limpia de conexiones en FastAPI.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.core.config import settings

# Motor de conexión SQLAlchemy adaptativo (PostgreSQL / SQLite)
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

engine_kwargs = {"echo": False}
if "sqlite" in db_url:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(db_url, **engine_kwargs)


# Fábrica de sesiones ORM
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db_session() -> Generator[Session, None, None]:
    """
    Generador de sesiones de base de datos para inyección de dependencias en FastAPI.
    Garantiza el cierre automático de la sesión al finalizar la petición HTTP.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def auto_patch_schema():
    """
    Garantiza que todas las tablas y columnas nuevas existan en PostgreSQL o SQLite
    sin requerir migraciones manuales en despliegues VPS.
    """
    from backend.models.base import Base
    import backend.models  # Registra todos los modelos ORM
    from sqlalchemy import text

    # 1. Crear cualquier tabla nueva no existente (ej. shift_closings, waste_logs, etc.)
    Base.metadata.create_all(bind=engine)

    # 2. Parchear columnas nuevas en tablas existentes para PostgreSQL
    if "sqlite" not in str(engine.url):
        with engine.connect() as conn:
            patches = [
                # Tabla orders (seguros operativos, idempotencia y cancelación)
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS client_order_id VARCHAR(100);",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS cancellation_reason TEXT;",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS cancelled_by_id UUID REFERENCES users(id);",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMP WITH TIME ZONE;",
                # Tabla products
                "ALTER TABLE products ADD COLUMN IF NOT EXISTS image_url VARCHAR(500);",
                # Tabla users
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS hashed_pin VARCHAR(255);",
                # Tabla machines
                "ALTER TABLE machines ADD COLUMN IF NOT EXISTS qr_code_token VARCHAR(255);",
                # Índice de idempotencia
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_orders_client_order_id ON orders(client_order_id) WHERE client_order_id IS NOT NULL;"
            ]
            for p in patches:
                try:
                    conn.execute(text(p))
                    conn.commit()
                except Exception as err:
                    print(f"[DB AUTO-PATCH] Nota: {err}")

