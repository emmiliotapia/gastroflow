"""
Módulo de Registro de Mermas y Desperdicios (`waste.py`)
======================================================
Este módulo define la entidad ORM `WasteLog` para el control y costeo de
mermas de ingredientes o productos descartados en cocina, barra o almacén.
"""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Enum, ForeignKey, Numeric, String, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin
from backend.models.enums import StockLocation

if TYPE_CHECKING:
    from backend.models.ingredient import Ingredient
    from backend.models.product import Product
    from backend.models.user import User


class WasteLog(Base, TimestampMixin):
    """
    Modelo de la tabla 'waste_logs'.
    Registro de desperdicios o mermas con justificación y valorización monetaria perdida.
    """

    __tablename__ = "waste_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único UUID del registro de merma"
    )

    ingredient_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Clave foránea opcional del ingrediente mermado"
    )

    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Clave foránea opcional del producto directo mermado"
    )

    location: Mapped[StockLocation] = mapped_column(
        Enum(StockLocation, name="stock_location_enum", create_type=False),
        nullable=False,
        index=True,
        comment="Ubicación donde ocurrió la merma (KITCHEN, BAR, WAREHOUSE)"
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False,
        comment="Cantidad mermada de insumo o producto"
    )

    reason: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Justificación de la merma (ej. Expiración, Caída, Error de preparación)"
    )

    total_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        default=Decimal("0.0000"),
        nullable=False,
        comment="Valor total monetario de la merma (quantity * cost_per_unit)"
    )

    recorded_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Usuario supervisor o colaborador que registró la merma"
    )

    # Relaciones
    ingredient: Mapped[Optional["Ingredient"]] = relationship("Ingredient")
    product: Mapped[Optional["Product"]] = relationship("Product")
    recorded_by: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        return f"<WasteLog(location='{self.location.value}', qty={self.quantity}, cost=${self.total_cost}, reason='{self.reason}')>"
