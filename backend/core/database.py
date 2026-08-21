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

# Motor de conexión SQLAlchemy para PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False
)

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
