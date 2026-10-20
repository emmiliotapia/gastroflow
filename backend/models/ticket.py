"""
Módulo de Modelo de Tickets de Mantenimiento / Sistemas
======================================================
Este módulo define el modelo ORM `Ticket` para la gestión de incidencias,
reportes de fallas en slots y solicitudes de sistemas en el casino.
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin
from backend.models.enums import TicketStatus
from backend.models.machine import Machine
from backend.models.user import User


class Ticket(Base, TimestampMixin):
    """
    Modelo de la tabla 'tickets'.
    Representa un ticket de soporte técnico para una máquina tragamonedas o área general de la sala.
    """

    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único del ticket"
    )

    folio: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Folio incremental único (ej. TKT-00001)"
    )

    machine_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("machines.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Máquina/slot reportada"
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Detalle o descripción de la falla o solicitud de sistemas"
    )

    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status_enum", create_type=True),
        default=TicketStatus.PENDIENTE,
        nullable=False,
        comment="Estado actual del ticket (PENDIENTE, EN_PROCESO, HOLD, FINALIZADO)"
    )

    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Usuario (Staff o Mesero) que reportó el incidente (o NULL si es reporte de cliente por QR)"
    )


    assigned_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Técnico asignado a la resolución"
    )

    closed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Jefe de sala o Admin que autorizó y cerró el ticket con PIN"
    )

    resolution_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Comentarios explicativos del técnico sobre la solución"
    )

    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha y hora en la que se cerró formalmente el ticket"
    )

    # Relaciones ORM
    machine: Mapped[Optional["Machine"]] = relationship("Machine")
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id])
    assigned_to: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to_id])
    closed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[closed_by_id])

    def __repr__(self) -> str:
        return f"<Ticket(folio='{self.folio}', status='{self.status.value}', machine='{self.machine_id}')>"
