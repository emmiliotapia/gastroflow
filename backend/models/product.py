"""
Módulo de Modelo de Productos Finales AyB y Recetas
===================================================
Este módulo define los modelos ORM `Product` y `RecipeItem`.
- `Product`: Representa el producto listo para consumo en casino (comanda / pedido QR).
- `RecipeItem`: Tabla relacional intermedia que define los ingredientes y cantidades
  que consume un producto preparado (subreceta / costeo por platillo o bebida).
"""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, Enum, ForeignKey, Numeric, String, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin
from backend.models.enums import KDSStation, ProductType, UnitOfMeasure

if TYPE_CHECKING:
    from backend.models.ingredient import Ingredient


class Product(Base, TimestampMixin):
    """
    Modelo de la tabla 'products'.
    Representa un producto del catálogo de Alimentos y Bebidas (AyB).
    Soporta productos preparados con receta (Cocina/Barra) y productos directos de almacén.
    """

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único UUID del producto final"
    )

    sku: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Código SKU único del producto (ej. AYB-101)"
    )

    name: Mapped[str] = mapped_column(
        String(120),
        index=True,
        nullable=False,
        comment="Nombre comercial del producto (ej. Hamburguesa Cheeseburger, Coctel Margarita)"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Descripción detallada del producto para la PWA de pedidos"
    )

    category: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
        comment="Categoría del menú (ej. Coctelería, Entradas, Platos Fuertes, Bebidas Embotelladas)"
    )

    product_type: Mapped[ProductType] = mapped_column(
        Enum(ProductType, name="product_type_enum", create_type=True),
        nullable=False,
        comment="Diferenciador de inventario: PREPARED (descuenta receta) o DIRECT (descuenta stock propio)"
    )

    destination_kds: Mapped[KDSStation] = mapped_column(
        Enum(KDSStation, name="kds_station_enum", create_type=True),
        nullable=False,
        comment="Estación KDS donde debe aparecer la comanda (KITCHEN, BAR, etc.)"
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Precio público de venta o costo equivalente de cortesía"
    )

    courtesy_tier_min: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Nivel mínimo de membresía del cliente para cortesía gratuita (ej. GOLD, PLATINUM, VIP)"
    )

    current_stock: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        default=Decimal("0.0000"),
        nullable=False,
        comment="Existencias directas (solo aplica para productos de tipo DIRECT como refrescos o cervezas)"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Indica si el producto está disponible en el menú activo"
    )

    # Relación uno-a-muchos con los elementos de la receta
    recipe_items: Mapped[List["RecipeItem"]] = relationship(
        "RecipeItem",
        back_populates="product",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Product(sku='{self.sku}', name='{self.name}', type={self.product_type.value}, kds={self.destination_kds.value})>"


class RecipeItem(Base, TimestampMixin):
    """
    Modelo de la tabla 'recipe_items'.
    Relación N:M entre Productos y sus Ingredientes constituyentes con la dosificación requerida.
    """

    __tablename__ = "recipe_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único UUID del elemento de receta"
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Clave foránea hacia el producto preparado"
    )

    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Clave foránea hacia el ingrediente consumido"
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False,
        comment="Cantidad requerida del ingrediente para preparar 1 unidad del producto"
    )

    unit_of_measure: Mapped[UnitOfMeasure] = mapped_column(
        Enum(UnitOfMeasure, name="unit_of_measure_enum", create_type=False),
        nullable=False,
        comment="Unidad de medida de la dosificación en la receta"
    )

    # Relaciones relacionales
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="recipe_items"
    )

    ingredient: Mapped["Ingredient"] = relationship(
        "Ingredient",
        back_populates="recipe_items"
    )

    def __repr__(self) -> str:
        return f"<RecipeItem(product_id='{self.product_id}', ingredient_id='{self.ingredient_id}', qty={self.quantity})>"
