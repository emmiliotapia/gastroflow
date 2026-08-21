"""
Esquemas Pydantic para Catálogos y Recetas (`catalog.py`)
=========================================================
Este módulo contiene los esquemas DTO (Data Transfer Objects) para la gestión
de Ingredientes, Productos de Alimentos y Bebidas (AyB) y Fichas Técnicas de Recetas.
"""

import uuid
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.models.enums import KDSStation, ProductType, UnitOfMeasure


# ------------------------------------------------------------------------------
# Esquemas para Ingredientes
# ------------------------------------------------------------------------------

class IngredientBase(BaseModel):
    code: str = Field(..., example="ING-PAN-01", description="Código interno único del ingrediente")
    name: str = Field(..., example="Pan Brioche para Hamburguesa", description="Nombre del insumo")
    unit_of_measure: UnitOfMeasure = Field(..., description="Unidad de medida (KG, G, L, ML, PIECE, etc.)")
    cost_per_unit: Decimal = Field(..., ge=0, example=8.50, description="Costo unitario con precisión de 4 decimales")
    current_stock: Decimal = Field(default=Decimal("0.0000"), ge=0, description="Existencias en almacén")
    minimum_stock: Decimal = Field(default=Decimal("0.0000"), ge=0, description="Stock mínimo para alertas")


class IngredientCreate(IngredientBase):
    """Esquema para crear un nuevo ingrediente."""
    pass


class IngredientUpdate(BaseModel):
    """Esquema para actualización parcial de un ingrediente."""
    name: Optional[str] = None
    unit_of_measure: Optional[UnitOfMeasure] = None
    cost_per_unit: Optional[Decimal] = Field(None, ge=0)
    current_stock: Optional[Decimal] = Field(None, ge=0)
    minimum_stock: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None


class IngredientRead(IngredientBase):
    """Esquema de lectura de un ingrediente."""
    id: uuid.UUID
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------------------------
# Esquemas para Elementos de Receta (RecipeItem)
# ------------------------------------------------------------------------------

class RecipeItemCreate(BaseModel):
    ingredient_id: uuid.UUID = Field(..., description="UUID del ingrediente requerido")
    quantity: Decimal = Field(..., gt=0, example=200.0, description="Cantidad/gramaje necesario por platillo")
    unit_of_measure: UnitOfMeasure = Field(..., description="Unidad de medida de la dosificación")


class RecipeItemRead(BaseModel):
    id: Optional[uuid.UUID] = None
    ingredient_id: Optional[uuid.UUID] = None
    ingredient_code: Optional[str] = None
    ingredient_name: Optional[str] = None
    quantity: Decimal
    unit_of_measure: UnitOfMeasure
    unit_cost: Decimal = Field(..., description="Costo unitario del ingrediente")
    subtotal_cost: Decimal = Field(..., description="Costo calculado (quantity * unit_cost)")

    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------------------------
# Esquemas para Productos Finales AyB
# ------------------------------------------------------------------------------

class ProductBase(BaseModel):
    sku: str = Field(..., example="AYB-BBQ-01", description="Código SKU del producto final")
    name: str = Field(..., example="Hamburguesa BBQ Especial", description="Nombre del platillo o bebida")
    description: Optional[str] = Field(None, example="Hamburguesa con 200g de Sirloin, tocino ahumado y salsa BBQ artesanal")
    category: str = Field(..., example="Hamburguesas Gourmet", description="Categoría de menú")
    product_type: ProductType = Field(..., description="PREPARED (con receta) o DIRECT (venta directa)")
    destination_kds: KDSStation = Field(..., description="Estación KDS destino (KITCHEN, BAR, etc.)")
    price: Decimal = Field(..., ge=0, example=240.00, description="Precio de venta al público")
    courtesy_tier_min: Optional[str] = Field(None, example="GOLD", description="Membresía mínima para cortesía libre")
    current_stock: Decimal = Field(default=Decimal("0.0000"), ge=0, description="Stock directo (solo para tipo DIRECT)")


class ProductCreate(ProductBase):
    """Esquema para crear un producto final con opción de incluir su receta inicial."""
    recipe_items: Optional[List[RecipeItemCreate]] = Field(default=[], description="Lista de insumos si el tipo es PREPARED")


class ProductUpdate(BaseModel):
    """Esquema para actualizar un producto."""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    product_type: Optional[ProductType] = None
    destination_kds: Optional[KDSStation] = None
    price: Optional[Decimal] = Field(None, ge=0)
    courtesy_tier_min: Optional[str] = None
    current_stock: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ProductRead(ProductBase):
    """Esquema de lectura de producto con detalle de receta y costo total de producción."""
    id: Optional[uuid.UUID] = None
    is_active: bool = True
    current_stock: Decimal = Field(default=Decimal("0.0000"), ge=0)
    recipe_items: List[RecipeItemRead] = Field(default=[], description="Ficha técnica de insumos constituyentes")
    total_production_cost: Decimal = Field(default=Decimal("0.0000"), description="Costo total de producción derivado de la receta")

    model_config = ConfigDict(from_attributes=True)


class RecipeCostSummary(BaseModel):
    """Esquema de resumen de costeo de receta."""
    product_id: uuid.UUID
    product_sku: str
    product_name: str
    sale_price: Decimal
    total_production_cost: Decimal
    profit_margin_amount: Decimal = Field(..., description="Margen bruto en dinero (price - cost)")
    profit_margin_percent: Decimal = Field(..., description="Porcentaje de margen bruto de ganancia")
    recipe_items: List[RecipeItemRead]
