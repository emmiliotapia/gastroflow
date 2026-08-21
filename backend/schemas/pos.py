"""
Esquemas Pydantic para Configuración del POS (`pos.py`)
======================================================
Este módulo contiene las representaciones de entrada/salida para la administración
de categorías y botones de la cuadrícula táctil del Punto de Venta.
"""

import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class POSButtonCreate(BaseModel):
    category_id: uuid.UUID = Field(..., description="ID de la categoría contenedora")
    product_id: uuid.UUID = Field(..., description="ID del producto de AyB asociado")
    label: str = Field(..., max_length=100, example="Hamburguesa BBQ", description="Texto visible en el botón")
    color_class: Optional[str] = Field(None, example="bg-amber-500", description="Clase CSS para styling de UI")
    display_order: int = Field(0, ge=0, description="Orden relativo en el grid")


class POSButtonRead(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    product_id: uuid.UUID
    label: str
    color_class: Optional[str] = None
    display_order: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class POSCategoryCreate(BaseModel):
    name: str = Field(..., max_length=100, example="Especialidades", description="Nombre único de la categoría")
    color_theme: Optional[str] = Field(default="blue", example="amber", description="Tema visual general de la pestaña")
    display_order: int = Field(0, ge=0, description="Posición relativa de visualización")


class POSCategoryRead(BaseModel):
    id: uuid.UUID
    name: str
    color_theme: Optional[str] = None
    display_order: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class POSCategoryWithButtonsRead(POSCategoryRead):
    buttons: List[POSButtonRead] = []

    model_config = ConfigDict(from_attributes=True)
