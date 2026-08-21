"""
Esquemas Pydantic para Comandas y KDS (`order.py`)
=================================================
Este módulo define las estructuras de datos DTO para la creación de pedidos,
su desglose de líneas y la actualización de estados operativos desde pantallas KDS.
"""

import uuid
from decimal import Decimal
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.models.enums import OrderStatus


class OrderItemCreate(BaseModel):
    product_id: uuid.UUID = Field(..., description="ID del producto AyB a ordenar")
    quantity: Decimal = Field(..., gt=0, example=1, description="Cantidad ordenada")


class OrderItemRead(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    product_id: uuid.UUID
    product_name: Optional[str] = Field(None, alias="product_name", description="Nombre del producto (cargado dinámicamente)")
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class OrderCreate(BaseModel):
    machine_id: Optional[uuid.UUID] = Field(None, description="UUID de la máquina/slot si el pedido viene de escaneo QR")
    notes: Optional[str] = Field(None, example="Sin cebolla, aderezo extra", description="Notas de preparación")
    items: List[OrderItemCreate] = Field(..., min_length=1, description="Detalle de productos ordenados")
    supervisor_pin: Optional[str] = Field(None, description="PIN opcional de supervisor para autorizar cortesía si excede el nivel")


class OrderRead(BaseModel):
    id: uuid.UUID
    machine_id: Optional[uuid.UUID] = None
    order_number: str
    status: OrderStatus
    total_amount: Decimal
    notes: Optional[str] = None
    created_by_id: Optional[uuid.UUID] = None
    created_at: Any
    items: List[OrderItemRead] = []

    model_config = ConfigDict(from_attributes=True)


class KDSOrderUpdate(BaseModel):
    status: OrderStatus = Field(..., description="Nuevo estado de la comanda (ej. PREPARING, READY, DELIVERED)")
