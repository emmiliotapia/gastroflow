"""
Módulo de Configuración de la Botonera y Categorías del POS (`pos.py`)
====================================================================
Este módulo contiene los modelos ORM que definen las categorías visuales
y los botones interactivos del Punto de Venta (POS) para Alimentos y Bebidas.
"""

import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, ForeignKey, Integer, String, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.models.product import Product


class POSCategory(Base, TimestampMixin):
    """
    Modelo de la tabla 'pos_categories'.
    Agrupaciones lógicas de productos en la interfaz táctil/móvil (ej. Botanas, Cocteles).
    """

    __tablename__ = "pos_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único UUID de la categoría del POS"
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="Nombre único de la categoría"
    )

    color_theme: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        default="blue",
        comment="Color primario para distinguir la pestaña/sección en la UI"
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Orden secuencial para ordenar las categorías de izquierda a derecha"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Indica si la categoría se muestra activa en el POS"
    )

    # Relación de uno a muchos con botones
    buttons: Mapped[List["POSButton"]] = relationship(
        "POSButton",
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="POSButton.display_order"
    )

    def __repr__(self) -> str:
        return f"<POSCategory(name='{self.name}', order={self.display_order})>"


class POSButton(Base, TimestampMixin):
    """
    Modelo de la tabla 'pos_buttons'.
    Botón visual configurable dentro del grid del POS que enlaza directamente a un producto.
    """

    __tablename__ = "pos_buttons"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único del botón"
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pos_categories.id", ondelete="CASCADE"),
        nullable=False,
        comment="Clave foránea hacia la categoría contenedora"
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        comment="Clave foránea hacia el producto que representa el botón"
    )

    label: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Etiqueta o texto que se pintará en el botón de la UI"
    )

    color_class: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Estilo/clase de color del botón específico en la rejilla"
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Posición del botón dentro del grid de la categoría"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Indica si el botón está disponible"
    )

    # Relaciones
    category: Mapped["POSCategory"] = relationship("POSCategory", back_populates="buttons")
    product: Mapped["Product"] = relationship("Product")

    def __repr__(self) -> str:
        return f"<POSButton(label='{self.label}', order={self.display_order})>"
