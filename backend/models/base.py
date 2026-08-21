"""
Módulo Base de la Capa de Datos (ORM)
=====================================
Este módulo define la clase base declarativa de SQLAlchemy 2.0 y el Mixin de
marcas de tiempo (TimestampMixin) para auditar la creación y actualización
de registros en la base de datos PostgreSQL.
"""

from datetime import datetime, timezone
from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Clase base declarativa de la cual heredan todos los modelos ORM.
    Proporciona la infraestructura central para el mapeo de tablas en SQLAlchemy 2.0.
    """
    pass


class TimestampMixin:
    """
    Mixin reutilizable que agrega campos automáticos de auditoría temporal
    (created_at y updated_at) a cualquier modelo que lo herede.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Fecha y hora de creación del registro en formato UTC"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Fecha y hora de la última actualización del registro en formato UTC"
    )
