"""
Módulo de Cierre de Turno y Arqueo Financiero (Reporte Z) (`shift.py`)
====================================================================
Este módulo define la entidad ORM `ShiftClosing` para capturar de manera inmutable
los arqueos de caja, diferencias de efectivo, ventas netas y autorizaciones con PIN.
"""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.models.user import User


class ShiftClosing(Base, TimestampMixin):
    """
    Modelo de la tabla 'shift_closings'.
    Registro inmutable de cierre de turno y arqueo de caja (Reporte Z).
    """

    __tablename__ = "shift_closings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único del cierre de turno"
    )

    folio: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="Folio del corte de caja (ej. CRTE-20260823-01)"
    )

    shift_date: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Fecha operativa del turno (YYYY-MM-DD)"
    )

    cashier_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Nombre del cajero o responsable del turno"
    )

    expected_cash: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Efectivo teórico calculado según comandas cobradas en CASH"
    )

    declared_cash: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Efectivo físico real contado en caja"
    )

    difference: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Diferencia de efectivo (declared_cash - expected_cash)"
    )

    card_total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Total cobrado con tarjeta bancaria"
    )

    courtesy_total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Valor nominal total de cortesías otorgadas"
    )

    total_sales: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Ventas netas totales (Efectivo + Tarjeta)"
    )

    total_waste: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Total monetario de mermas registradas en el turno"
    )

    net_balance: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Balance neto del turno (total_sales - total_waste)"
    )

    paid_orders_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        comment="Cantidad de comandas liquidadas"
    )

    complimentary_orders_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        comment="Cantidad de comandas de cortesía autorizadas"
    )

    supervisor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Supervisor que validó el arqueo con PIN"
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Observaciones o incidencias del turno"
    )

    # Relaciones
    supervisor: Mapped[Optional["User"]] = relationship("User")
