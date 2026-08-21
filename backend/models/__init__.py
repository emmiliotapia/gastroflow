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
    OrderStatus,
    ProductType,
    StockLocation,
    StockTransactionType,
    TicketStatus,
    UnitOfMeasure,
    UserRole,
)
from backend.models.ingredient import Ingredient
from backend.models.machine import Machine
from backend.models.order import Order, OrderItem
from backend.models.pos import POSButton, POSCategory
from backend.models.product import Product, RecipeItem
from backend.models.stock import StockLevel, StockTransaction
from backend.models.user import Role, User
from backend.models.waste import WasteLog

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
    "StockLocation",
    "StockTransactionType",
    "OrderStatus",
    # Models
    "Ingredient",
    "Product",
    "RecipeItem",
    "Machine",
    "Role",
    "User",
    "StockLevel",
    "StockTransaction",
    "WasteLog",
    "Order",
    "OrderItem",
    "POSCategory",
    "POSButton",
]
