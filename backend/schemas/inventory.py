"""
Esquemas Pydantic para Inventario, Mermas y POS (`inventory.py`)
==============================================================
Este módulo define los esquemas DTO (Data Transfer Objects) para:
- Niveles de stock por bodega/estación.
- Transacciones y compras de inventario.
- Porcionado y conversión de insumos.
- Registro y reporte de mermas.
- Alertas automáticas de desabastecimiento.
- Simulación de comanda POS con descuento atómico.
"""

import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.models.enums import StockLocation, StockTransactionType, UnitOfMeasure


class StockLevelRead(BaseModel):
    id: uuid.UUID
    ingredient_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    location: StockLocation
    quantity: Decimal
    ingredient_name: Optional[str] = None
    product_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class StockTransactionCreate(BaseModel):
    location: StockLocation = Field(..., description="Bodega o estación de destino/origen")
    transaction_type: StockTransactionType = Field(..., description="Tipo de movimiento (PURCHASE, ADJUSTMENT, etc.)")
    quantity: Decimal = Field(..., description="Cantidad de movimiento (Positiva para compras/entradas, negativa para ajustes)")
    ingredient_id: Optional[uuid.UUID] = Field(None, description="UUID del ingrediente")
    product_id: Optional[uuid.UUID] = Field(None, description="UUID del producto directo")
    unit_cost: Optional[Decimal] = Field(None, ge=0, description="Costo unitario registrado en la compra")
    notes: Optional[str] = Field(None, example="Compra según Factura #F-4902", description="Notas o folios explicativos")


class StockTransactionRead(BaseModel):
    id: uuid.UUID
    ingredient_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    location: StockLocation
    transaction_type: StockTransactionType
    quantity: Decimal
    unit_cost: Decimal
    notes: Optional[str] = None
    created_at: Any

    model_config = ConfigDict(from_attributes=True)


class PortioningRequest(BaseModel):
    macro_ingredient_id: uuid.UUID = Field(..., description="UUID del insumo macro a porcionar (ej. 1 KG Sirloin)")
    micro_ingredient_id: uuid.UUID = Field(..., description="UUID del insumo porcionado micro (ej. Porción 200g Sirloin)")
    macro_quantity: Decimal = Field(..., gt=0, example=1.0, description="Cantidad macro consumida")
    conversion_factor: Decimal = Field(..., gt=0, example=5.0, description="Porciones micro resultantes por cada unidad macro")
    location: StockLocation = Field(default=StockLocation.KITCHEN, description="Bodega donde se realiza la preparación")
    notes: Optional[str] = Field(None, example="Porcionado de carne para turno nocturno")


class WasteLogCreate(BaseModel):
    location: StockLocation = Field(..., description="Ubicación donde ocurrió la merma")
    quantity: Decimal = Field(..., gt=0, example=2.5, description="Cantidad desperdiciada o mermada")
    reason: str = Field(..., example="Expiración de caducidad en refrigerador", description="Justificación detallada")
    ingredient_id: Optional[uuid.UUID] = Field(None, description="UUID del ingrediente mermado")
    product_id: Optional[uuid.UUID] = Field(None, description="UUID del producto mermado")


class WasteLogRead(BaseModel):
    id: uuid.UUID
    ingredient_id: Optional[uuid.UUID] = None
    ingredient_name: Optional[str] = None
    product_id: Optional[uuid.UUID] = None
    product_name: Optional[str] = None
    location: StockLocation
    quantity: Decimal
    reason: str
    total_cost: Decimal = Field(..., description="Costo valorizado de la pérdida")
    recorded_by_id: Optional[uuid.UUID] = None
    recorded_by_name: Optional[str] = None
    created_at: Any

    model_config = ConfigDict(from_attributes=True)



class LowStockAlertRead(BaseModel):
    ingredient_id: str
    code: str
    name: str
    unit: str
    current_stock: float
    minimum_stock: float
    deficit: float
    suggested_purchase_quantity: float
    unit_cost: float
    estimated_purchase_cost: float
    severity: str


class POSDeductRequest(BaseModel):
    product_id: uuid.UUID = Field(..., description="UUID del producto ordenado en la comanda")
    order_quantity: Decimal = Field(default=Decimal("1.0000"), gt=0, description="Cantidad de productos solicitados")
    location: Optional[StockLocation] = Field(None, description="Estación de descuento (si no se especifica, usa KDS por defecto)")


class POSDeductResponse(BaseModel):
    status: str
    product_sku: str
    product_name: str
    order_quantity: float
    location: str
    deducted_components: List[Dict[str, Any]]
