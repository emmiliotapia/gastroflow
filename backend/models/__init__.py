"""
Paquete Central de Modelos ORM (`backend.models`)
=================================================
Este paquete exporta todas las entidades relacionales, la clase Base declarativa
y las enumeraciones del sistema para simplificar su importación en routers FastAPI,
servicios de negocio y configuraciones de Alembic.
"""

from backend.models.base import Base, TimestampMixin
from backend.models.enums import (
    KDSStation,
    MachineStatus,
    ProductType,
    TicketStatus,
    UnitOfMeasure,
    UserRole,
)
from backend.models.ingredient import Ingredient
from backend.models.machine import Machine
from backend.models.product import Product, RecipeItem
from backend.models.user import Role, User

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    # Enums
    "UnitOfMeasure",
    "ProductType",
    "KDSStation",
    "MachineStatus",
    "UserRole",
    "TicketStatus",
    # Models
    "Ingredient",
    "Product",
    "RecipeItem",
    "Machine",
    "Role",
    "User",
]
