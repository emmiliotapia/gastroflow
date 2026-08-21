"""
Módulo de Usuarios, Roles y Seguridad (Poka-Yoke)
=================================================
Este módulo contiene los modelos ORM `Role` y `User`.
Incluye soporte para control de acceso RBAC y el campo de seguridad `hashed_pin`
utilizado de manera independiente por los Jefes de Sala (`JEFE_DE_SALA`) para autorizar
operaciones críticas en sala (cortesías excedidas, cierre de tickets).
"""

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin
from backend.models.enums import UserRole, MembershipTier


class Role(Base, TimestampMixin):
    """
    Modelo de la tabla 'roles'.
    Representa el rol del usuario en el sistema con permisos estructurados.
    """

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identificador entero autoincremental del rol"
    )

    name: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum", create_type=True),
        unique=True,
        nullable=False,
        comment="Nombre del rol del sistema (ADMIN, JEFE_DE_SALA, WAITER, etc.)"
    )

    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Descripción detallada de las responsabilidades del rol"
    )

    permissions: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Matriz JSON con permisos granulares (ej. {'ayb': ['read', 'approve'], 'tickets': ['close']})"
    )

    # Relación uno-a-muchos con usuarios
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="role"
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name.value}')>"


class User(Base, TimestampMixin):
    """
    Modelo de la tabla 'users'.
    Representa a un empleado o usuario registrado en el ecosistema.
    Soporta autenticación estándar por contraseña y autenticación secundaria por PIN/NIP para Jefes de Sala.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único UUID del usuario"
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Nombre de usuario único para acceso al sistema"
    )

    email: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Correo electrónico institucional o personal"
    )

    full_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        comment="Nombre completo del usuario / colaborador"
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Hash seguro de la contraseña principal (Bcrypt/Argon2)"
    )

    hashed_pin: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Hash seguro del NIP/PIN numérico de 4 a 6 dígitos (Exclusivo Poka-Yoke para Jefes de Sala)"
    )

    membership_tier: Mapped[Optional[MembershipTier]] = mapped_column(
        Enum(MembershipTier, name="membership_tier_enum", create_type=True),
        default=MembershipTier.CLASSIC,
        nullable=True,
        comment="Nivel de membresía del cliente para cortesías (CLASSIC, GOLD, PLATINUM, VIP)"
    )

    role_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Clave foránea hacia el rol asignado al usuario"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Indica si la cuenta de usuario se encuentra activa"
    )

    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha y hora de la última sesión iniciada en formato UTC"
    )

    # Relaciones relacionales
    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="users"
    )

    def __repr__(self) -> str:
        return f"<User(username='{self.username}', name='{self.full_name}', role_id={self.role_id})>"
