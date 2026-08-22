"""
Módulo de Modelo de Ingredientes e Insumos
=========================================
Este módulo define el modelo ORM `Ingredient` utilizado para la gestión de
inventario base, costos por unidad y control de stock mínimo en cocina y barra.
"""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, Enum, Numeric, String, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin
from backend.models.enums import UnitOfMeasure

if TYPE_CHECKING:
    from backend.models.product import RecipeItem


class Ingredient(Base, TimestampMixin):
    """
    Modelo de la tabla 'ingredients'.
    Representa un insumo o ingrediente prima (ej. Carne molida, Pan, Limón, Jarabe de goma).
    """

    __tablename__ = "ingredients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único UUID del ingrediente"
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Código interno único del ingrediente (ej. ING-001)"
    )

    name: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
        comment="Nombre del ingrediente o insumo (ej. Carne de Res 150g)"
    )

    unit_of_measure: Mapped[UnitOfMeasure] = mapped_column(
        Enum(UnitOfMeasure, name="unit_of_measure_enum", create_type=True),
        nullable=False,
        comment="Unidad de medida estandarizada para costeo y descuento de inventario"
    )

    category: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        default="ABARROTES",
        comment="Categoría del insumo (PROTEINAS, VEGETALES, LACTEOS, PANADERIA, ABARROTES, LICORES, etc.)"
    )

    sub_recipe_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="ID de producto/subreceta vinculada si es un insumo elaborado"
    )

    cost_per_unit: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        default=Decimal("0.0000"),
        nullable=False,
        comment="Costo unitario del ingrediente con 4 decimales de precisión"
    )

    current_stock: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        default=Decimal("0.0000"),
        nullable=False,
        comment="Existencias actuales en inventario"
    )

    minimum_stock: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        default=Decimal("0.0000"),
        nullable=False,
        comment="Stock mínimo para disparar alertas de reabastecimiento"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Indica si el ingrediente está activo para su uso en recetas"
    )

    # Relación uno-a-muchos con la tabla intermedia de recetas
    recipe_items: Mapped[List["RecipeItem"]] = relationship(
        "RecipeItem",
        back_populates="ingredient",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Ingredient(code='{self.code}', name='{self.name}', stock={self.current_stock} {self.unit_of_measure.value})>"
