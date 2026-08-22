"""
Módulo de Modelo de Clientes VIP y Padrón de Cortesías (`vip_client.py`)
========================================================================
Este módulo define la entidad ORM `VIPClient` utilizada para registrar a los
jugadores VIP del casino, controlar su nivel de membresía (Plata, Oro, Platino, Prestige)
y verificar automáticamente su derecho a cortesías en Alimentos y Bebidas.
"""

import uuid
from typing import Optional
from sqlalchemy import Boolean, Enum, Integer, String, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin
from backend.models.enums import MembershipTier


class VIPClient(Base, TimestampMixin):
    """
    Modelo de la tabla 'vip_clients'.
    Representa a un cliente del padrón VIP de Marketing del casino.
    """

    __tablename__ = "vip_clients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único UUID del cliente VIP"
    )

    client_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Código único de cliente de marketing (ej. VIP-1001)"
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
        index=True,
        nullable=False,
        comment="Nombre completo del socio o cliente VIP"
    )

    card_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=True,
        comment="Número o track magnético de la tarjeta de socio"
    )

    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Teléfono de contacto o WhatsApp"
    )

    tier: Mapped[MembershipTier] = mapped_column(
        Enum(MembershipTier, name="membership_tier_enum", create_type=False),
        default=MembershipTier.PLATA,
        nullable=False,
        index=True,
        comment="Nivel de membresía activo (PLATA/CLASSIC, ORO/GOLD, PLATINO/PLATINUM, PRESTIGE/VIP)"
    )

    daily_courtesy_limit: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
        comment="Límite diario de cortesías autorizadas según tabulador"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Indica si el socio se encuentra habilitado para cortesías"
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Preferencias de A&B (ej. Bebida favorita, alergias, área habitual)"
    )

    def __repr__(self) -> str:
        return f"<VIPClient(code='{self.client_code}', name='{self.full_name}', tier='{self.tier.value}')>"
