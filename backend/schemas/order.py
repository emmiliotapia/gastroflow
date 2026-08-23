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

from backend.models.enums import OrderStatus, PaymentStatus, KDSStation


class OrderItemCreate(BaseModel):
    product_id: uuid.UUID = Field(..., description="ID del producto AyB a ordenar")
    quantity: Decimal = Field(..., gt=0, example=1, description="Cantidad ordenada")
    is_courtesy: Optional[bool] = Field(False, description="Indica si se otorga como cortesía")


class OrderItemRead(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    product_id: uuid.UUID
    product_name: Optional[str] = Field(None, alias="product_name", description="Nombre del producto")
    destination_kds: Optional[KDSStation] = Field(None, description="Estación KDS destino (KITCHEN, BAR)")
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class OrderCreate(BaseModel):
    machine_id: Optional[uuid.UUID] = Field(None, description="UUID de la máquina/slot si el pedido viene de escaneo QR")
    machine_code: Optional[str] = Field(None, description="Código de máquina/slot alternativo (ej. SLOT-101, 000)")
    client_order_id: Optional[str] = Field(None, description="UUID o token de idempotencia para prevenir duplicados por doble click")
    notes: Optional[str] = Field(None, example="Sin cebolla, aderezo extra", description="Notas de preparación")
    items: List[OrderItemCreate] = Field(..., min_length=1, description="Detalle de productos ordenados")
    supervisor_pin: Optional[str] = Field(None, description="PIN opcional de supervisor para autorizar cortesía si excede el nivel")
    client_name: Optional[str] = Field(None, description="Nombre o identificación de cliente VIP si aplica")


class OrderRead(BaseModel):
    id: uuid.UUID
    machine_id: Optional[uuid.UUID] = None
    machine_code: Optional[str] = Field(None, description="Código de activo de la máquina (ej. SLOT-101 o 000)")
    order_number: str
    client_order_id: Optional[str] = None
    status: OrderStatus
    total_amount: Decimal
    payment_status: PaymentStatus
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = None
    cancelled_by_name: Optional[str] = Field(None, description="Nombre del supervisor que autorizó la cancelación")
    cancelled_at: Optional[Any] = None
    created_by_id: Optional[uuid.UUID] = None
    created_by_name: Optional[str] = Field(None, description="Nombre del mesero o cajero que levantó la orden")
    created_at: Any
    items: List[OrderItemRead] = []

    model_config = ConfigDict(from_attributes=True)


class KDSOrderUpdate(BaseModel):
    status: OrderStatus = Field(..., description="Nuevo estado de la comanda (ej. PREPARING, READY, DELIVERED)")


class OrderPay(BaseModel):
    payment_method: str = Field(..., example="CASH", description="Método de pago (CASH, CARD, COURTESY)")
    supervisor_pin: Optional[str] = Field(None, min_length=4, max_length=6, description="PIN opcional de supervisor si se autoriza cortesía de última hora")


class OrderCancel(BaseModel):
    supervisor_pin: str = Field(..., min_length=4, max_length=6, description="PIN de supervisor obligatorio para autorizar la cancelación")
    reason: str = Field(..., min_length=3, max_length=255, description="Motivo justificado de la cancelación")



