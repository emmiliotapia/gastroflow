"""
Módulo de Modelo de Máquinas de Casino (Slots / Terminales)
==========================================================
Este módulo define el modelo ORM `Machine` para gestionar el inventario de
máquinas tragamonedas (slots) o terminales en la sala de juego, su ubicación por zonas
y la vinculación con tokens de código QR.
"""

import uuid
from typing import Optional
from sqlalchemy import Boolean, Enum, String, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin
from backend.models.enums import MachineStatus


class Machine(Base, TimestampMixin):
    """
    Modelo de la tabla 'machines'.
    Representa una máquina tragamonedas (slot) o estación física identificada por un código QR.
    """

    __tablename__ = "machines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único UUID de la máquina"
    )

    serial_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Número de serie físico único asignado por el fabricante"
    )

    asset_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Código numérico o identificador de activo en sala (ej. SLOT-402, M-105)"
    )

    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Modelo y marca de la máquina (ej. Bally Alpha II, IGT PeakSlant)"
    )

    zone: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
        comment="Zona física de la sala donde se ubica (ej. Zona VIP, Piso Principal, Fumadores)"
    )

    qr_code_token: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Token único embebido en la URL del código QR estático adherido a la máquina (?machine_id=...)"
    )

    status: Mapped[MachineStatus] = mapped_column(
        Enum(MachineStatus, name="machine_status_enum", create_type=True),
        default=MachineStatus.OPERATIONAL,
        nullable=False,
        comment="Estado operativo actual de la máquina (OPERATIONAL, MAINTENANCE, OUT_OF_SERVICE)"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Indica si la máquina está dada de alta en el sistema"
    )

    def __repr__(self) -> str:
        return f"<Machine(asset_code='{self.asset_code}', serial='{self.serial_number}', zone='{self.zone}', status={self.status.value})>"
