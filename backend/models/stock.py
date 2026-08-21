"""
Módulo de Gestión de Inventario Físico y Movimientos (`stock.py`)
================================================================
Este módulo define las entidades ORM `StockLevel` y `StockTransaction` para el
control de existencias segmentado por bodega/estación (Almacén, Cocina, Barra)
y el registro auditable de entradas, compras, traspasos y descuentos.
"""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Enum, ForeignKey, Numeric, String, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin
from backend.models.enums import StockLocation, StockTransactionType

if TYPE_CHECKING:
    from backend.models.ingredient import Ingredient
    from backend.models.product import Product
    from backend.models.user import User


class StockLevel(Base, TimestampMixin):
    """
    Modelo de la tabla 'stock_levels'.
    Almacena los balances físicos vigentes de un ingrediente o producto en una ubicación específica.
    """

    __tablename__ = "stock_levels"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único UUID del nivel de stock"
    )

    ingredient_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Clave foránea opcional hacia el ingrediente (si aplica)"
    )

    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Clave foránea opcional hacia el producto directo (si aplica)"
    )

    location: Mapped[StockLocation] = mapped_column(
        Enum(StockLocation, name="stock_location_enum", create_type=True),
        nullable=False,
        index=True,
        comment="Ubicación o bodega física (WAREHOUSE, KITCHEN, BAR)"
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        default=Decimal("0.0000"),
        nullable=False,
        comment="Cantidad disponible actual en esta ubicación"
    )

    # Relaciones
    ingredient: Mapped[Optional["Ingredient"]] = relationship("Ingredient")
    product: Mapped[Optional["Product"]] = relationship("Product")

    def __repr__(self) -> str:
        return f"<StockLevel(location='{self.location.value}', qty={self.quantity})>"


class StockTransaction(Base, TimestampMixin):
    """
    Modelo de la tabla 'stock_transactions'.
    Registro histórico e inmutable de movimientos de inventario (compras, ajustes, ventas, traspasos).
    """

    __tablename__ = "stock_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único UUID de la transacción"
    )

    ingredient_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Clave foránea opcional hacia el ingrediente afectado"
    )

    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Clave foránea opcional hacia el producto directo afectado"
    )

    location: Mapped[StockLocation] = mapped_column(
        Enum(StockLocation, name="stock_location_enum", create_type=False),
        nullable=False,
        index=True,
        comment="Bodega o estación donde se registró el movimiento"
    )

    transaction_type: Mapped[StockTransactionType] = mapped_column(
        Enum(StockTransactionType, name="stock_transaction_type_enum", create_type=True),
        nullable=False,
        comment="Tipo de transacción (PURCHASE, ADJUSTMENT, WASTE, SALE_DEDUCTION, etc.)"
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False,
        comment="Cantidad de movimiento (Positivo para entradas, negativo para salidas)"
    )

    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        default=Decimal("0.0000"),
        nullable=False,
        comment="Costo unitario registrado en el momento de la transacción"
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Notas explicativas, folio de compra o justificación de ajuste"
    )

    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Usuario que registró la transacción"
    )

    # Relaciones
    ingredient: Mapped[Optional["Ingredient"]] = relationship("Ingredient")
    product: Mapped[Optional["Product"]] = relationship("Product")
    created_by: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        return f"<StockTransaction(type='{self.transaction_type.value}', location='{self.location.value}', qty={self.quantity})>"
