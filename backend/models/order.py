"""
Módulo de Gestión de Comandas y Detalle de Pedidos (`order.py`)
=============================================================
Este módulo define las entidades relacionales `Order` y `OrderItem`
para capturar comisiones de venta de AyB vinculadas a slots/mesas.
"""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Enum, ForeignKey, Numeric, String, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin
from backend.models.enums import OrderStatus

if TYPE_CHECKING:
    from backend.models.machine import Machine
    from backend.models.product import Product
    from backend.models.user import User


class Order(Base, TimestampMixin):
    """
    Modelo de la tabla 'orders'.
    Cabecera del pedido de alimentos o bebidas.
    """

    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único de la comanda"
    )

    machine_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("machines.id", ondelete="SET NULL"),
        nullable=True,
        comment="Clave foránea opcional de la máquina/slot desde donde se originó el pedido"
    )

    order_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="Código o folio de comanda autogenerado (ej. COM-00124)"
    )

    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status_enum", create_type=True),
        default=OrderStatus.PENDING,
        nullable=False,
        comment="Estado operativo del pedido"
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Total monetario cobrado de la comanda"
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Comentarios especiales (ej. Sin cebolla, Aderezo extra)"
    )

    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Usuario mesero o administrador que levantó la orden"
    )

    # Relaciones
    machine: Mapped[Optional["Machine"]] = relationship("Machine")
    created_by: Mapped[Optional["User"]] = relationship("User")
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Order(folio='{self.order_number}', status='{self.status.value}', total=${self.total_amount})>"


class OrderItem(Base, TimestampMixin):
    """
    Modelo de la tabla 'order_items'.
    Detalle de productos solicitados en la comanda.
    """

    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único del renglón"
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        comment="Clave foránea hacia la cabecera de la orden"
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Clave foránea hacia el producto consumido"
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Cantidad ordenada de unidades del producto"
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Precio unitario cobrado al momento de la orden"
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Monto subtotal calculado (quantity * unit_price)"
    )

    # Relaciones
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product")

    def __repr__(self) -> str:
        return f"<OrderItem(product_id='{self.product_id}', qty={self.quantity}, subtotal=${self.subtotal})>"
